import { createHash, createHmac } from "node:crypto";
import { PassThrough } from "node:stream";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import PDFDocument from "pdfkit";

const WATCHDOG_VERSION = "0.1.0";

export interface FindingReceiptInput {
  findingId: string;
  /** Full JSON report body to hash and optionally pin */
  reportJson: Record<string, unknown>;
  researcherHandle: string;
  disclosureTargetEmail: string;
  disclosedAt: Date;
}

export interface ReceiptArtifacts {
  receiptUrl: string;
  ipfsCid: string;
  sha256: string;
  pdfBuffer: Buffer;
  signedReceipt: SignedReceiptPayload;
  receiptHmac: string;
}

export interface SignedReceiptPayload {
  finding_id: string;
  sha256: string;
  ipfs_cid: string;
  researcher_handle_hash: string;
  disclosed_at: string;
  zwanski_watchdog_version: string;
}

export interface DisclosureEnv {
  ipfsApiUrl: string;
  minioEndpoint: string;
  minioPort: number;
  minioUseSsl: boolean;
  minioAccessKey: string;
  minioSecretKey: string;
  receiptBucket: string;
  /** HMAC secret to "sign" receipt payload (replace with Ed25519 in production) */
  receiptSigningSecret: string;
}

/**
 * Builds SHA256 disclosure receipts, optional IPFS pin, and PDF upload to MinIO.
 */
export class ReceiptGenerator {
  constructor(private readonly env: DisclosureEnv) {}

  /**
   * Produce hash, IPFS CID (or dev placeholder), PDF, and signed receipt object.
   */
  async generate(input: FindingReceiptInput): Promise<ReceiptArtifacts> {
    const body = Buffer.from(JSON.stringify(input.reportJson, null, 2), "utf8");
    const sha256 = createHash("sha256").update(body).digest("hex");
    const ipfsCid = await this.pinToIpfs(body);
    const handleHash = createHash("sha256")
      .update(input.researcherHandle, "utf8")
      .digest("hex");

    const signedReceipt: SignedReceiptPayload = {
      finding_id: input.findingId,
      sha256,
      ipfs_cid: ipfsCid,
      researcher_handle_hash: handleHash,
      disclosed_at: input.disclosedAt.toISOString(),
      zwanski_watchdog_version: WATCHDOG_VERSION,
    };

    const signature = createHmac("sha256", this.env.receiptSigningSecret)
      .update(JSON.stringify(signedReceipt))
      .digest("hex");

    const pdfBuffer = await this.buildPdf({
      ...signedReceipt,
      disclosure_target: input.disclosureTargetEmail,
      receipt_hmac: signature,
    });

    const objectKey = `receipts/${input.findingId}.pdf`;
    const receiptUrl = await this.uploadPdf(objectKey, pdfBuffer);

    return {
      receiptUrl,
      ipfsCid,
      sha256,
      pdfBuffer,
      signedReceipt,
      receiptHmac: signature,
    };
  }

  private async pinToIpfs(body: Buffer): Promise<string> {
    if (!this.env.ipfsApiUrl || this.env.ipfsApiUrl.includes("disable")) {
      return `local-${createHash("sha256").update(body).digest("hex").slice(0, 16)}`;
    }
    const form = new FormData();
    form.append("file", new Blob([body]), "report.json");
    const res = await fetch(`${this.env.ipfsApiUrl.replace(/\/$/, "")}/add?pin=true`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      throw new Error(`IPFS add failed: ${res.status} ${await res.text()}`);
    }
    const json = (await res.json()) as { Hash?: string; cid?: string };
    return json.Hash ?? json.cid ?? "unknown-cid";
  }

  private async uploadPdf(key: string, pdf: Buffer): Promise<string> {
    const client = new S3Client({
      region: "us-east-1",
      endpoint: `${this.env.minioUseSsl ? "https" : "http"}://${this.env.minioEndpoint}:${this.env.minioPort}`,
      credentials: {
        accessKeyId: this.env.minioAccessKey,
        secretAccessKey: this.env.minioSecretKey,
      },
      forcePathStyle: true,
    });
    await client.send(
      new PutObjectCommand({
        Bucket: this.env.receiptBucket,
        Key: key,
        Body: pdf,
        ContentType: "application/pdf",
      }),
    );
    return `${this.env.minioEndpoint}:${this.env.minioPort}/${this.env.receiptBucket}/${key}`;
  }

  private buildPdf(fields: Record<string, string>): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      const doc = new PDFDocument({ size: "A4", margin: 50 });
      const stream = new PassThrough();
      const chunks: Buffer[] = [];
      stream.on("data", (c) => chunks.push(c as Buffer));
      stream.on("end", () => resolve(Buffer.concat(chunks)));
      stream.on("error", reject);
      doc.pipe(stream);
      doc.fontSize(20).text("Zwanski Watchdog", { underline: true });
      doc.moveDown();
      doc.fontSize(11).text("Signed disclosure receipt", { align: "left" });
      doc.moveDown();
      Object.entries(fields).forEach(([k, v]) => {
        doc.fontSize(10).text(`${k}: ${v}`, { width: 500 });
      });
      doc.end();
    });
  }
}
