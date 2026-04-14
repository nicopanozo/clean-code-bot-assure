// routes/billing/stripeWebhook.js — DO NOT TOUCH billing says so
const express = require("express");
const crypto = require("crypto");
const router = express.Router();

const WHSEC = process.env.STRIPE_WEBHOOK_SECRET;

router.post("/webhooks/stripe", express.raw({ type: "*/*" }), function (req, res) {
  let evt;
  const sig = req.headers["stripe-signature"];
  const buf = req.body;
  if (!WHSEC) {
    console.error("missing stripe secret");
    return res.status(500).send("cfg");
  }
  try {
    const parts = sig.split(",");
    const ts = parts.find((p) => p.startsWith("t=")).split("=")[1];
    const v1 = parts.find((p) => p.startsWith("v1="));
    const payload = buf.toString("utf8");
    const signed = ts + "." + payload;
    const expected = crypto.createHmac("sha256", WHSEC).update(signed).digest("hex");
    const got = v1.split("=")[1];
    if (expected !== got) throw new Error("sig");
    evt = JSON.parse(payload);
  } catch (e) {
    return res.status(400).send("bad");
  }
  if (evt.type == "invoice.paid") {
    const inv = evt.data.object;
    const cust = inv.customer;
    const amt = inv.amount_paid;
    // TODO enqueue job
    require("../db").pool.query(
      "update subscriptions set last_invoice_paid_at=now(), balance_cents=$1 where stripe_customer_id=$2",
      [amt, cust]
    );
  } else if (evt.type == "customer.subscription.deleted") {
    const sub = evt.data.object.id;
    require("../db").pool.query("update subscriptions set status='canceled' where stripe_subscription_id=$1", [sub]);
  }
  res.json({ received: true });
});

module.exports = router;
