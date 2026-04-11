import { createHash, createHmac } from "node:crypto";
import type { SignedReceiptPayload } from "./receipt.js";

export interface VerifyInput {
  receipt: SignedReceiptPayload;
  receiptHmac: string;
  reportJsonBody: string;
  signingSecret: string;
}

export interface VerifyResult {
  valid: boolean;
  reasons: string[];
}

/**
 * Verifies receipt SHA256 matches report body and HMAC signature.
 */
export class ReceiptVerifier {
  verify(input: VerifyInput): VerifyResult {
    const reasons: string[] = [];
    const expected = createHash("sha256").update(input.reportJsonBody, "utf8").digest("hex");
    if (expected !== input.receipt.sha256) {
      reasons.push("sha256_mismatch");
    }
    if (!input.receiptHmac) {
      reasons.push("missing_signature");
    } else {
      const mac = createHmac("sha256", input.signingSecret)
        .update(JSON.stringify(input.receipt))
        .digest("hex");
      if (mac !== input.receiptHmac) {
        reasons.push("signature_mismatch");
      }
    }
    return { valid: reasons.length === 0, reasons };
  }

  /**
   * Verify IPFS content matches expected hash (caller fetches bytes from gateway).
   */
  verifyIpfsContent(bytes: Buffer, expectedSha256: string): boolean {
    const h = createHash("sha256").update(bytes).digest("hex");
    return h === expectedSha256;
  }
}
