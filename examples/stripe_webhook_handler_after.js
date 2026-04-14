/**
 * Stripe webhook ingress for the billing service.
 *
 * Verifies the ``Stripe-Signature`` header (HMAC v1 scheme), then dispatches a small set of
 * subscription lifecycle events into our Postgres mirror. Idempotency is handled upstream
 * by Stripe event IDs; this handler stays intentionally thin.
 */

const express = require("express");
const crypto = require("crypto");
const { pool } = require("../db");

const router = express.Router();

/** @type {string|undefined} */
const WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET;

/**
 * Parse ``t`` and ``v1`` fields from the Stripe-Signature header.
 * @param {string} headerValue
 * @returns {{ timestamp: string, signature: string }}
 */
function parseStripeSignature(headerValue) {
  const chunks = headerValue.split(",").map((part) => part.trim());
  const timestampChunk = chunks.find((c) => c.startsWith("t="));
  const v1Chunk = chunks.find((c) => c.startsWith("v1="));
  if (!timestampChunk || !v1Chunk) {
    throw new Error("Malformed Stripe-Signature header");
  }
  return {
    timestamp: timestampChunk.split("=")[1],
    signature: v1Chunk.split("=")[1],
  };
}

/**
 * @param {string} signingSecret
 * @param {string} rawBody
 * @param {string} headerValue
 */
function verifyStripePayload(signingSecret, rawBody, headerValue) {
  const { timestamp, signature } = parseStripeSignature(headerValue);
  const signedPayload = `${timestamp}.${rawBody}`;
  const expected = crypto.createHmac("sha256", signingSecret).update(signedPayload).digest("hex");
  const expectedBuf = Buffer.from(expected, "hex");
  const signatureBuf = Buffer.from(signature, "hex");
  if (
    expectedBuf.length !== signatureBuf.length ||
    !crypto.timingSafeEqual(expectedBuf, signatureBuf)
  ) {
    throw new Error("Signature mismatch");
  }
  return JSON.parse(rawBody);
}

/** @param {{ type: string, data: { object: Record<string, unknown> } }} event */
async function handleStripeEvent(event) {
  if (event.type === "invoice.paid") {
    const invoice = event.data.object;
    await pool.query(
      `update subscriptions
         set last_invoice_paid_at = now(),
             balance_cents = $1
       where stripe_customer_id = $2`,
      [invoice.amount_paid, invoice.customer]
    );
    return;
  }

  if (event.type === "customer.subscription.deleted") {
    const subscriptionId = event.data.object.id;
    await pool.query(
      `update subscriptions
         set status = 'canceled'
       where stripe_subscription_id = $1`,
      [subscriptionId]
    );
  }
}

router.post("/webhooks/stripe", express.raw({ type: "*/*" }), async (req, res) => {
  if (!WEBHOOK_SECRET) {
    req.log?.error("STRIPE_WEBHOOK_SECRET is not configured");
    return res.status(500).send("configuration_error");
  }

  const signature = req.headers["stripe-signature"];
  if (typeof signature !== "string") {
    return res.status(400).send("missing_signature");
  }

  let event;
  try {
    const rawBody = req.body.toString("utf8");
    event = verifyStripePayload(WEBHOOK_SECRET, rawBody, signature);
  } catch (err) {
    return res.status(400).send("invalid_payload");
  }

  try {
    await handleStripeEvent(event);
  } catch (err) {
    req.log?.error({ err }, "stripe_webhook_handler_failed");
    return res.status(500).send("handler_error");
  }

  return res.json({ received: true });
});

module.exports = router;
