# -*- coding: utf-8 -*-
import hashlib
import logging
import struct
import time
from binascii import hexlify

import ecdsa

from .account import PrivateKey, PublicKey
from .py23 import bytes_types, py23_bytes

log = logging.getLogger(__name__)

SECP256K1_MODULE = None
SECP256K1_AVAILABLE = False
CRYPTOGRAPHY_AVAILABLE = False
GMPY2_MODULE = False
if not SECP256K1_MODULE:
    try:
        import secp256k1prp as secp256k1

        SECP256K1_MODULE = "secp256k1"
        SECP256K1_AVAILABLE = True
    except:
        try:
            import secp256k1

            SECP256K1_MODULE = "secp256k1"
            SECP256K1_AVAILABLE = True
        except ImportError:
            try:
                import cryptography

                SECP256K1_MODULE = "cryptography"
                CRYPTOGRAPHY_AVAILABLE = True
            except ImportError:
                SECP256K1_MODULE = "ecdsa"

    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import (
            decode_dss_signature,
            encode_dss_signature,
        )

        CRYPTOGRAPHY_AVAILABLE = True
    except ImportError:
        CRYPTOGRAPHY_AVAILABLE = False
        log.debug("Cryptography not available")

log.debug("Using SECP256K1 module: %s" % SECP256K1_MODULE)


def _is_canonical(sig):
    sig = bytearray(sig)
    return (
        not (int(sig[0]) & 0x80)
        and not (sig[0] == 0 and not (int(sig[1]) & 0x80))
        and not (int(sig[32]) & 0x80)
        and not (sig[32] == 0 and not (int(sig[33]) & 0x80))
    )


def compressedPubkey(pk):
    if SECP256K1_MODULE == "cryptography" and not isinstance(pk, ecdsa.keys.VerifyingKey):
        order = ecdsa.SECP256k1.order
        x = pk.public_numbers().x
        y = pk.public_numbers().y
    else:
        order = pk.curve.generator.order()
        p = pk.pubkey.point
        x = p.x()
        y = p.y()
    x_str = ecdsa.util.number_to_string(x, order)
    return py23_bytes(chr(2 + (y & 1)), "ascii") + x_str


def recover_public_key(digest, signature, i, message=None):
    """Recover the public key from the the signature"""

    # See http: //www.secg.org/download/aid-780/sec1-v2.pdf section 4.1.6 primarily
    curve = ecdsa.SECP256k1.curve
    G = ecdsa.SECP256k1.generator
    order = ecdsa.SECP256k1.order
    yp = i % 2
    r, s = ecdsa.util.sigdecode_string(signature, order)
    # 1.1
    x = r + (i // 2) * order
    # 1.3. This actually calculates for either effectively 02||X or 03||X depending on 'k' instead of always for 02||X as specified.
    # This substitutes for the lack of reversing R later on. -R actually is defined to be just flipping the y-coordinate in the elliptic curve.
    alpha = ((x * x * x) + (curve.a() * x) + curve.b()) % curve.p()
    beta = ecdsa.numbertheory.square_root_mod_prime(alpha, curve.p())
    y = beta if (beta - yp) % 2 == 0 else curve.p() - beta
    # 1.4 Constructor of Point is supposed to check if nR is at infinity.
    R = ecdsa.ellipticcurve.Point(curve, x, y, order)
    # 1.5 Compute e
    e = ecdsa.util.string_to_number(digest)
    # 1.6 Compute Q = r^-1(sR - eG)
    Q = ecdsa.numbertheory.inverse_mod(r, order) * (s * R + (-e % order) * G)

    if SECP256K1_MODULE == "cryptography" and message is not None:
        if not isinstance(message, bytes_types):
            message = py23_bytes(message, "utf-8")
        sigder = encode_dss_signature(r, s)
        try:
            Q_point = Q.to_affine()
            public_key = ec.EllipticCurvePublicNumbers(
                Q_point.x(), Q_point.y(), ec.SECP256K1()
            ).public_key(default_backend())
        except:
            try:
                public_key = ec.EllipticCurvePublicNumbers(
                    Q._Point__x, Q._Point__y, ec.SECP256K1()
                ).public_key(default_backend())
            except:
                Q_point = Q.to_affine()
                public_key = ec.EllipticCurvePublicNumbers(
                    int(Q_point.x()), int(Q_point.y()), ec.SECP256K1()
                ).public_key(default_backend())
        public_key.verify(sigder, message, ec.ECDSA(hashes.SHA256()))
        return public_key
    else:
        # Not strictly necessary, but let's verify the message for paranoia's sake.
        if not ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1).verify_digest(
            signature, digest, sigdecode=ecdsa.util.sigdecode_string
        ):
            return None
        return ecdsa.VerifyingKey.from_public_point(Q, curve=ecdsa.SECP256k1)


def recoverPubkeyParameter(message, digest, signature, pubkey):
    """Use to derive a number that allows to easily recover the
    public key from the signature
    """
    if not isinstance(message, bytes_types):
        message = py23_bytes(message, "utf-8")
    for i in range(0, 4):
        if SECP256K1_MODULE == "secp256k1":
            sig = pubkey.ecdsa_recoverable_deserialize(signature, i)
            p = secp256k1.PublicKey(pubkey.ecdsa_recover(message, sig))
            if p.serialize() == pubkey.serialize():
                return i
        elif SECP256K1_MODULE == "cryptography" and not isinstance(pubkey, PublicKey):
            p = recover_public_key(digest, signature, i, message)
            p_comp = hexlify(compressedPubkey(p))
            pubkey_comp = hexlify(compressedPubkey(pubkey))
            if p_comp == pubkey_comp:
                return i
        else:  # pragma: no cover
            p = recover_public_key(digest, signature, i)
            p_comp = hexlify(compressedPubkey(p))
            p_string = hexlify(p.to_string())
            if isinstance(pubkey, PublicKey):
                pubkey_string = py23_bytes(repr(pubkey), "latin")
            else:  # pragma: no cover
                pubkey_string = hexlify(pubkey.to_string())
            if p_string == pubkey_string or p_comp == pubkey_string:
                return i
    return None


def sign_message(message, wif, hashfn=hashlib.sha256):
    """Sign a digest with a wif key

    :param str wif: Private key in
    """

    if not isinstance(message, bytes_types):
        message = py23_bytes(message, "utf-8")

    digest = hashfn(message).digest()
    priv_key = PrivateKey(wif)
    if SECP256K1_MODULE == "secp256k1":
        p = py23_bytes(priv_key)
        ndata = secp256k1.ffi.new("const int *ndata")
        ndata[0] = 0
        while True:
            ndata[0] += 1
            privkey = secp256k1.PrivateKey(p, raw=True)
            sig = secp256k1.ffi.new("secp256k1_ecdsa_recoverable_signature *")
            signed = secp256k1.lib.secp256k1_ecdsa_sign_recoverable(
                privkey.ctx, sig, digest, privkey.private_key, secp256k1.ffi.NULL, ndata
            )
            if not signed == 1:
                raise AssertionError()
            signature, i = privkey.ecdsa_recoverable_serialize(sig)
            if _is_canonical(signature):
                i += 4  # compressed
                i += 27  # compact
                break
    elif SECP256K1_MODULE == "cryptography":
        cnt = 0
        private_key = ec.derive_private_key(
            int(repr(priv_key), 16), ec.SECP256K1(), default_backend()
        )
        public_key = private_key.public_key()
        while True:
            cnt += 1
            if not cnt % 20:
                log.info("Still searching for a canonical signature. Tried %d times already!" % cnt)
            order = ecdsa.SECP256k1.order
            sigder = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(sigder)
            signature = ecdsa.util.sigencode_string(r, s, order)
            # Make sure signature is canonical!
            #
            sigder = bytearray(sigder)
            lenR = sigder[3]
            lenS = sigder[5 + lenR]
            if lenR == 32 and lenS == 32:
                # Derive the recovery parameter
                #
                i = recoverPubkeyParameter(message, digest, signature, public_key)
                i += 4  # compressed
                i += 27  # compact
                break
    else:  # pragma: no branch  # pragma: no cover
        cnt = 0
        p = py23_bytes(priv_key)
        sk = ecdsa.SigningKey.from_string(p, curve=ecdsa.SECP256k1)
        while 1:
            cnt += 1
            if not cnt % 20:
                log.info("Still searching for a canonical signature. Tried %d times already!" % cnt)

            # Deterministic k
            #
            k = ecdsa.rfc6979.generate_k(
                sk.curve.generator.order(),
                sk.privkey.secret_multiplier,
                hashlib.sha256,
                hashlib.sha256(
                    digest
                    + struct.pack("d", time.time())  # use the local time to randomize the signature
                ).digest(),
            )

            # Sign message
            #
            sigder = sk.sign_digest(digest, sigencode=ecdsa.util.sigencode_der, k=k)

            # Reformating of signature
            #
            r, s = ecdsa.util.sigdecode_der(sigder, sk.curve.generator.order())
            signature = ecdsa.util.sigencode_string(r, s, sk.curve.generator.order())

            # Make sure signature is canonical!
            #
            sigder = bytearray(sigder)
            lenR = sigder[3]
            lenS = sigder[5 + lenR]
            if lenR == 32 and lenS == 32:
                # Derive the recovery parameter
                #
                i = recoverPubkeyParameter(message, digest, signature, sk.get_verifying_key())
                i += 4  # compressed
                i += 27  # compact
                break

    # pack signature
    #
    sigstr = struct.pack("<B", i)
    sigstr += signature

    return sigstr


def verify_message(message, signature, hashfn=hashlib.sha256, recover_parameter=None):
    if not isinstance(message, bytes_types):
        message = py23_bytes(message, "utf-8")
    if not isinstance(signature, bytes_types):
        signature = py23_bytes(signature, "utf-8")
    if not isinstance(message, bytes_types):
        raise AssertionError()
    if not isinstance(signature, bytes_types):
        raise AssertionError()
    digest = hashfn(message).digest()
    sig = signature[1:]
    if recover_parameter is None:
        recover_parameter = bytearray(signature)[0] - 4 - 27  # recover parameter only
    if recover_parameter < 0:
        log.info("Could not recover parameter")
        return None

    if SECP256K1_MODULE == "secp256k1":
        ALL_FLAGS = secp256k1.lib.SECP256K1_CONTEXT_VERIFY | secp256k1.lib.SECP256K1_CONTEXT_SIGN
        # Placeholder
        pub = secp256k1.PublicKey(flags=ALL_FLAGS)
        # Recover raw signature
        sig = pub.ecdsa_recoverable_deserialize(sig, recover_parameter)
        # Recover PublicKey
        verifyPub = secp256k1.PublicKey(pub.ecdsa_recover(message, sig))
        # Convert recoverable sig to normal sig
        normalSig = verifyPub.ecdsa_recoverable_convert(sig)
        # Verify
        verifyPub.ecdsa_verify(message, normalSig)
        phex = verifyPub.serialize(compressed=True)
    elif SECP256K1_MODULE == "cryptography":
        p = recover_public_key(digest, sig, recover_parameter, message)
        order = ecdsa.SECP256k1.order
        r, s = ecdsa.util.sigdecode_string(sig, order)
        sigder = encode_dss_signature(r, s)
        p.verify(sigder, message, ec.ECDSA(hashes.SHA256()))
        phex = compressedPubkey(p)
    else:  # pragma: no branch  # pragma: no cover
        p = recover_public_key(digest, sig, recover_parameter)
        # Will throw an exception of not valid
        p.verify_digest(sig, digest, sigdecode=ecdsa.util.sigdecode_string)
        phex = compressedPubkey(p)

    return phex


def tweakaddPubkey(pk, digest256, SECP256K1_MODULE=SECP256K1_MODULE):
    if SECP256K1_MODULE == "secp256k1":
        tmp_key = secp256k1.PublicKey(pubkey=bytes(pk), raw=True)
        new_key = tmp_key.tweak_add(digest256)  # <-- add
        raw_key = hexlify(new_key.serialize()).decode("ascii")
    else:
        raise Exception("Must have secp256k1 for `tweak_add`")
        # raw_key = ecmult(pk, 1, digest256, SECP256K1_MODULE)
    return PublicKey(raw_key, prefix=pk.prefix)
