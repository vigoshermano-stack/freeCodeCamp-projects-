/**
 * Cloudflare Worker edge buffer.
 *
 * Purpose: absorb bursts before they reach the origin relay. The Worker queues
 * the event in KV (durable at the edge) and forwards it immediately; if the
 * origin is unreachable, the KV entry survives and a Cron Trigger re-drives it.
 *
 * Deploy:  wrangler deploy
 * Secrets: wrangler secret put ORIGIN_URL
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (request.method !== 'POST' || !url.pathname.startsWith('/hooks/')) {
      return new Response('not found', { status: 404 });
    }

    const body = await request.text();
    const id = crypto.randomUUID();
    const record = {
      id,
      source: url.pathname.split('/').pop() || 'unnamed',
      body,
      receivedAt: Date.now(),
      attempts: 0,
    };

    // 1. Persist at the edge FIRST (durability before acknowledgement).
    await env.BUFFER.put(`event:${id}`, JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 7, // 7 days
    });

    // 2. Forward to the origin relay without blocking the sender.
    ctx.waitUntil(forward(env, record));

    return Response.json({ accepted: true, event_id: id }, { status: 202 });
  },

  /** Cron: retry anything still buffered (origin was down or slow). */
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(drain(env));
  },
};

async function forward(env, record) {
  try {
    const res = await fetch(env.ORIGIN_URL + '/hooks/' + record.source, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'idempotency-key': record.id,
      },
      body: record.body,
    });
    if (res.ok) {
      await env.BUFFER.delete(`event:${record.id}`);
    }
  } catch (err) {
    // Leave it in KV; the cron will pick it up.
    console.log('forward failed', record.id, err.message);
  }
}

async function drain(env) {
  const list = await env.BUFFER.list({ prefix: 'event:', limit: 100 });
  for (const key of list.keys) {
    const raw = await env.BUFFER.get(key.name);
    if (!raw) continue;
    const record = JSON.parse(raw);
    record.attempts += 1;
    if (record.attempts > 20) {
      // Give up: move to a dead-letter key so it is never silently lost.
      await env.BUFFER.put(`dead:${record.id}`, raw);
      await env.BUFFER.delete(key.name);
      continue;
    }
    await env.BUFFER.put(key.name, JSON.stringify(record));
    await forward(env, record);
  }
}
