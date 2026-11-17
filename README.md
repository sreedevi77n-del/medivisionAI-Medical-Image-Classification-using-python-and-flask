# AGENTS.md: MediVision AI

## Architecture
- `public/`: the static site (publish directory). 15 hand-written HTML pages share `js/app.js` (API helper, sidebar/topbar layout, scan-status handling, heatmap renderer) and `css/style.css` (the design system, including dark theme and print styles). There is no bundler or framework, so keep it that way.
- `netlify/server/index.ts`: the single Netlify Server entry (Hono). `config.path` limits it to `/api/*` and `/uploads/*`; everything else is a static file.
- `server/`: server modules. `auth.ts` handles scrypt passwords and opaque session tokens stored hashed in the `sessions` table. `analyze.ts` runs the Gemini vision call and writes the result. `storage.ts` covers the Blobs store and Image CDN URL builders.
- `db/schema.ts`: Drizzle schema (the source of truth). Migrations live in `netlify/database/migrations/` and are generated with `drizzle-kit generate --name ...`. Never edit applied migrations.

## Scan lifecycle
1. `POST /api/predict` stores the (browser-downscaled) image in the Blobs store `scan-images`, inserts a `scans` row with `status = processing`, starts `analyzeScan` via `getContext().waitUntil`, and returns 202 immediately. This avoids the server's 20-second response limit.
2. Result pages poll `GET /api/scans/:id` through `scanReady()` in `app.js` until the status becomes `done`, `rejected` (not a medical image) or `failed` (the page offers a retry through `POST /api/scans/:id/retry`). Rows stuck in `processing` for more than 3 minutes are reported as failed.
3. The heatmap is **not** a stored image. The model returns up to 5 regions (`box` = `[ymin,xmin,ymax,xmax]` normalised to 0–1000, plus `weight`). `heatmapURL()` in `app.js` renders a Gaussian/jet overlay on a canvas, either transparent or blended for the report.

## Conventions
- API responses use snake_case keys (`patient_id`, `scan_type`, `created`) because the pages were written against that shape. `toScan()` in the server does the mapping.
- Every user-facing image goes through `/.netlify/images?...` (scan URLs come from `imageUrls()`; marketing images in `public/img/` are referenced via the CDN with `w=` and `fm=webp`).
- Upload keys are random UUIDs. `/uploads/:key` is public by unguessable URL because the Image CDN cannot forward auth headers.
- There is no demo or sample data anywhere. Insights and analytics are computed from real rows only.
- Every query is scoped by `userId` from the session middleware.

## Possible next steps
Password reset by email, multi-user organisations and shared patients, DICOM upload support, and an admin view of support messages.

README.md
added
+45
# MediVision AI

Explainable AI for medical imaging. Clinicians upload an X-ray, CT or MRI and get back:

- a **Normal / Abnormal classification** with calibrated confidence and per-class probabilities
- **plain-language findings**, an impression, differential considerations and suggested next steps
- an **attention heatmap** with ranked regions of influence, so you can see where the AI looked
- a **printable report** with a clinician sign-off line

The workspace also covers scan history with search and filters, patient records, an image gallery, analytics, live model insights, profile settings and help and support.

> MediVision AI produces decision-support output only. It is not a diagnostic device, and every result must be reviewed by a qualified clinician.

## Technology

| Layer | What it uses |
|---|---|
| Frontend | Plain HTML, CSS and JavaScript in `public/` (no build step), Chart.js for charts |
| API | A Netlify Server (Hono) in `netlify/server/index.ts`, handling `/api/*` and `/uploads/*` |
| Data | Netlify Database (Postgres) through Drizzle ORM: users, sessions, scans, patients, support messages |
| Images | Netlify Blobs stores the uploaded scans. All images are served through the Netlify Image CDN |
| AI | Gemini vision model through Netlify AI Gateway (no API keys to manage) |

## Run locally

```bash
npm install
npx netlify dev --port 8889
```

Open http://localhost:8889, create an account and upload a scan.

## Database changes

Edit `db/schema.ts`, then generate a migration:

```bash
npx drizzle-kit generate --name <describe_change>
```

Netlify applies migrations automatically on deploy.

## Configuration

- `MV_VISION_MODEL` (optional) sets which AI Gateway vision model is used. The default is `gemini-3-flash-preview`, with `gemini-flash-latest` as the automatic fallback.

db/index.ts
added
+5
import { drizzle } from "drizzle-orm/netlify-db";
import * as schema from "./schema.js";

export const db = drizzle({ schema });
export * from "./schema.js";

db/schema.ts
added
+75
import { pgTable, serial, text, timestamp, integer, real, jsonb, uniqueIndex, index } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: serial().primaryKey(),
  name: text().notNull().default(""),
  email: text().notNull().unique(),
  role: text().notNull().default("Radiologist"),
  passwordHash: text("password_hash").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const sessions = pgTable("sessions", {
  tokenHash: text("token_hash").primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  expiresAt: timestamp("expires_at").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const scans = pgTable(
  "scans",
  {
    id: serial().primaryKey(),
    userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
    patientId: text("patient_id").notNull().default(""),
    scanType: text("scan_type").notNull().default("X-Ray"),
    // processing | done | rejected | failed
    status: text().notNull().default("processing"),
    label: text().notNull().default(""),
    confidence: real().notNull().default(0),
    probabilities: jsonb().$type<Record<string, number>>().notNull().default({}),
    findings: text().notNull().default(""),
    regions: jsonb().$type<Region[]>().notNull().default([]),
    details: jsonb().$type<ScanDetails>().notNull().default({}),
    imageKey: text("image_key").notNull(),
    model: text().notNull().default(""),
    durationMs: integer("duration_ms").notNull().default(0),
    error: text().notNull().default(""),
    createdAt: timestamp("created_at").defaultNow().notNull(),
  },
  (t) => [index("scans_user_idx").on(t.userId, t.createdAt)],
);

export const patients = pgTable(
  "patients",
  {
    id: serial().primaryKey(),
    userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
    pid: text().notNull(),
    name: text().notNull(),
    age: integer(),
    sex: text().notNull().default(""),
    notes: text().notNull().default(""),
    createdAt: timestamp("created_at").defaultNow().notNull(),
  },
  (t) => [uniqueIndex("patients_user_pid_idx").on(t.userId, t.pid)],
);

export const supportMessages = pgTable("support_messages", {
  id: serial().primaryKey(),
  userId: integer("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  kind: text().notNull().default("Support"),
  subject: text().notNull().default(""),
  message: text().notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export type Region = { label: string; weight: number; box: [number, number, number, number] };
export type ScanDetails = {
  bodyPart?: string;
  modalityDetected?: string;
  imageQuality?: string;
  impression?: string;
  recommendations?: string[];
  differentials?: string[];
};

drizzle.config.ts
added
+7
import { defineConfig } from "drizzle-kit";

export default defineConfig({
  dialect: "postgresql",
  schema: "./db/schema.ts",
  out: "netlify/database/migrations",
});

netlify.toml
added
+14
[build]
  publish = "public"

# Generated marketing images: long cache, served through the Image CDN
[[headers]]
  for = "/img/*"
  [headers.values]
    Cache-Control = "public, max-age=604800, must-revalidate"

[[headers]]
  for = "/*"
  [headers.values]
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"

netlify/database/migrations/20261117045419_create_medivision_tables/migration.sql
added
+61
CREATE TABLE "patients" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"pid" text NOT NULL,
	"name" text NOT NULL,
	"age" integer,
	"sex" text DEFAULT '' NOT NULL,
	"notes" text DEFAULT '' NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "scans" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"patient_id" text DEFAULT '' NOT NULL,
	"scan_type" text DEFAULT 'X-Ray' NOT NULL,
	"status" text DEFAULT 'processing' NOT NULL,
	"label" text DEFAULT '' NOT NULL,
	"confidence" real DEFAULT 0 NOT NULL,
	"probabilities" jsonb DEFAULT '{}' NOT NULL,
	"findings" text DEFAULT '' NOT NULL,
	"regions" jsonb DEFAULT '[]' NOT NULL,
	"details" jsonb DEFAULT '{}' NOT NULL,
	"image_key" text NOT NULL,
	"model" text DEFAULT '' NOT NULL,
	"duration_ms" integer DEFAULT 0 NOT NULL,
	"error" text DEFAULT '' NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "sessions" (
	"token_hash" text PRIMARY KEY,
	"user_id" integer NOT NULL,
	"expires_at" timestamp NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "support_messages" (
	"id" serial PRIMARY KEY,
	"user_id" integer NOT NULL,
	"kind" text DEFAULT 'Support' NOT NULL,
	"subject" text DEFAULT '' NOT NULL,
	"message" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" serial PRIMARY KEY,
	"name" text DEFAULT '' NOT NULL,
	"email" text NOT NULL UNIQUE,
	"role" text DEFAULT 'Radiologist' NOT NULL,
	"password_hash" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX "patients_user_pid_idx" ON "patients" ("user_id","pid");--> statement-breakpoint
CREATE INDEX "scans_user_idx" ON "scans" ("user_id","created_at");--> statement-breakpoint
ALTER TABLE "patients" ADD CONSTRAINT "patients_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "scans" ADD CONSTRAINT "scans_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "support_messages" ADD CONSTRAINT "support_messages_user_id_users_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;

netlify/database/migrations/20261117045419_create_medivision_tables/snapshot.json
added
+746
Load change
Large changes are not rendered by default.


netlify/server/index.ts
added
+396
// MediVision AI — Netlify Server (REST API + uploaded image serving).
// Static pages live in /public; this server only handles /api/* and /uploads/*.
import { Hono, type Context } from "hono";
import { getContext } from "@netlify/server";
import { randomUUID } from "node:crypto";
import { and, asc, avg, count, desc, eq, gte, ilike, inArray, lt, or, sql, type SQL } from "drizzle-orm";
import { db, patients, scans, supportMessages, users } from "../../db/index.js";
import { createSession, destroySession, hashPassword, userFromToken, verifyPassword } from "../../server/auth.js";
import { analyzeScan, VISION_MODEL } from "../../server/analyze.js";
import { imageStore, imageUrls, KEY_RE } from "../../server/storage.js";

type User = { id: number; name: string; email: string; role: string };
type Env = { Variables: { user: User } };

const app = new Hono<Env>();
const MAX_BYTES = 10 * 1024 * 1024;
const STALE_MS = 3 * 60 * 1000;
const SCAN_TYPES = ["X-Ray", "CT Scan", "MRI"];

const err = (c: Context, msg: string, status = 400) => c.json({ error: msg }, status as 400);
const bearer = (c: Context) => (c.req.header("Authorization") || "").replace(/^Bearer\s+/i, "").trim();
const body = async (c: Context): Promise<Record<string, any>> => {
  try {
    return await c.req.json();
  } catch {
    return {};
  }
};
const fmt = (d: Date) => new Date(d).toISOString().slice(0, 16).replace("T", " ");

/** Run work after the response is sent, keeping the server alive until it finishes. */
function background(p: Promise<unknown>) {
  try {
    getContext().waitUntil(p);
  } catch {
    p.catch((e) => console.error(e));
  }
}

function toScan(r: typeof scans.$inferSelect) {
  const stale = r.status === "processing" && Date.now() - new Date(r.createdAt).getTime() > STALE_MS;
  return {
    id: r.id,
    patient_id: r.patientId,
    scan_type: r.scanType,
    status: stale ? "failed" : r.status,
    error: stale ? "The analysis timed out. Please retry." : r.error,
    label: r.label,
    confidence: r.confidence,
    probabilities: r.probabilities,
    findings: r.findings,
    regions: r.regions,
    details: r.details,
    model: r.model,
    duration_ms: r.durationMs,
    created: fmt(r.createdAt),
    ...imageUrls(r.imageKey),
  };
}

function dateRange(c: Context, userId: number): SQL[] {
  const w: SQL[] = [eq(scans.userId, userId)];
  const from = c.req.query("from"), to = c.req.query("to");
  if (from && /^\d{4}-\d{2}-\d{2}$/.test(from)) w.push(gte(scans.createdAt, new Date(from + "T00:00:00Z")));
  if (to && /^\d{4}-\d{2}-\d{2}$/.test(to)) w.push(lt(scans.createdAt, new Date(new Date(to + "T00:00:00Z").getTime() + 86400_000)));
  return w;
}

app.onError((e, c) => {
  console.error(e);
  return err(c, "Something went wrong on our side. Please try again.", 500);
});

app.get("/api/health", (c) => c.json({ mode: "live", model: VISION_MODEL }));

// ---------- accounts ----------
app.post("/api/register", async (c) => {
  const d = await body(c);
  const email = String(d.email || "").trim().toLowerCase();
  const password = String(d.password || "");
  if (!/^\S+@\S+\.\S+$/.test(email) || password.length < 8) return err(c, "Valid email and 8+ character password required");
  const exists = await db.select({ id: users.id }).from(users).where(eq(users.email, email)).limit(1);
  if (exists.length) return err(c, "Email already registered", 409);
  await db.insert(users).values({
    name: String(d.name || "").trim().slice(0, 120),
    email,
    role: String(d.role || "Radiologist").slice(0, 60),
    passwordHash: await hashPassword(password),
  });
  return c.json({ ok: true }, 201);
});

app.post("/api/login", async (c) => {
  const d = await body(c);
  const [u] = await db.select().from(users).where(eq(users.email, String(d.email || "").trim().toLowerCase())).limit(1);
  if (!u || !(await verifyPassword(String(d.password || ""), u.passwordHash))) return err(c, "Wrong email or password", 401);
  return c.json({ token: await createSession(u.id), name: u.name, role: u.role });
});

// Everything below requires a session token.
app.use("/api/*", async (c, next) => {
  const user = await userFromToken(bearer(c));
  if (!user) return err(c, "Please log in again", 401);
  c.set("user", user);
  await next();
});

app.post("/api/logout", async (c) => {
  await destroySession(bearer(c));
  return c.json({ ok: true });
});

app.get("/api/me", (c) => {
  const { name, email, role } = c.get("user");
  return c.json({ name, email, role });
});

app.put("/api/me", async (c) => {
  const d = await body(c);
  const u = c.get("user");
  await db
    .update(users)
    .set({ name: String(d.name || "").slice(0, 120), role: String(d.role || u.role).slice(0, 60) })
    .where(eq(users.id, u.id));
  const [r] = await db.select({ name: users.name, email: users.email, role: users.role }).from(users).where(eq(users.id, u.id));
  return c.json(r);
});

app.post("/api/password", async (c) => {
  const d = await body(c);
  const u = c.get("user");
  const [row] = await db.select({ pw: users.passwordHash }).from(users).where(eq(users.id, u.id));
  if (!(await verifyPassword(String(d.old || ""), row.pw))) return err(c, "Current password is wrong", 403);
  if (String(d.new || "").length < 8) return err(c, "New password needs 8+ characters");
  await db.update(users).set({ passwordHash: await hashPassword(String(d.new)) }).where(eq(users.id, u.id));
  return c.json({ ok: true });
});

// ---------- scans ----------
app.post("/api/predict", async (c) => {
  const u = c.get("user");
  const form = await c.req.formData().catch(() => null);
  const f = form?.get("image");
  if (!f || typeof f === "string") return err(c, "Upload a JPG or PNG image");
  const type = f.type.toLowerCase();
  const ext = type === "image/png" ? "png" : type === "image/webp" ? "webp" : type === "image/jpeg" ? "jpg" : "";
  if (!ext) return err(c, "Upload a JPG or PNG image (DICOM needs conversion first)");
  if (f.size > MAX_BYTES) return err(c, "File is larger than 10 MB");
  if (f.size < 1024) return err(c, "File is not a valid image");

  const key = `${randomUUID()}.${ext}`;
  await imageStore().set(key, await f.arrayBuffer(), { metadata: { contentType: type } });

  const scanType = SCAN_TYPES.includes(String(form!.get("scan_type"))) ? String(form!.get("scan_type")) : "X-Ray";
  const [row] = await db
    .insert(scans)
    .values({
      userId: u.id,
      patientId: String(form!.get("patient_id") || "").trim().slice(0, 64),
      scanType,
      imageKey: key,
      status: "processing",
    })
    .returning({ id: scans.id });

  background(analyzeScan(row.id));
  return c.json({ id: row.id, status: "processing" }, 202);
});

app.get("/api/scans", async (c) => {
  const u = c.get("user");
  const where = dateRange(c, u.id);
  const q = (c.req.query("q") || "").trim();
  if (q) {
    const like = `%${q}%`;
    where.push(or(ilike(scans.patientId, like), ilike(scans.label, like), sql`CAST(${scans.id} AS TEXT) LIKE ${like}`)!);
  }
  const t = c.req.query("type");
  if (t) where.push(eq(scans.scanType, t));
  const page = Math.max(parseInt(c.req.query("page") || "1") || 1, 1);
  const per = Math.min(Math.max(parseInt(c.req.query("per") || "8") || 8, 1), 50);
  const [{ n }] = await db.select({ n: count() }).from(scans).where(and(...where));
  const rows = await db
    .select()
    .from(scans)
    .where(and(...where))
    .orderBy(desc(scans.id))
    .limit(per)
    .offset((page - 1) * per);
  return c.json({ total: n, items: rows.map(toScan) });
});

app.delete("/api/scans", async (c) => {
  const u = c.get("user");
  const rows = await db.delete(scans).where(eq(scans.userId, u.id)).returning({ key: scans.imageKey });
  const store = imageStore();
  background(Promise.allSettled(rows.map((r) => store.delete(r.key))));
  return c.json({ ok: true, deleted: rows.length });
});

app.get("/api/scans/:id", async (c) => {
  const u = c.get("user");
  const id = parseInt(c.req.param("id"));
  if (!id) return err(c, "Scan not found", 404);
  const [r] = await db.select().from(scans).where(and(eq(scans.id, id), eq(scans.userId, u.id))).limit(1);
  if (!r) return err(c, "Scan not found", 404);
  const [p] = r.patientId
    ? await db.select().from(patients).where(and(eq(patients.userId, u.id), eq(patients.pid, r.patientId))).limit(1)
    : [];
  return c.json({
    ...toScan(r),
    disclaimer: "Decision-support output only. Not a confirmed diagnosis.",
    patient: p ? { id: p.id, pid: p.pid, name: p.name, age: p.age, sex: p.sex, notes: p.notes } : null,
  });
});

app.post("/api/scans/:id/retry", async (c) => {
  const u = c.get("user");
  const id = parseInt(c.req.param("id"));
  const [r] = await db
    .update(scans)
    .set({ status: "processing", error: "", createdAt: new Date() })
    .where(and(eq(scans.id, id), eq(scans.userId, u.id)))
    .returning({ id: scans.id });
  if (!r) return err(c, "Scan not found", 404);
  background(analyzeScan(r.id));
  return c.json({ id: r.id, status: "processing" }, 202);
});

app.delete("/api/scans/:id", async (c) => {
  const u = c.get("user");
  const id = parseInt(c.req.param("id"));
  const rows = await db
    .delete(scans)
    .where(and(eq(scans.id, id), eq(scans.userId, u.id)))
    .returning({ key: scans.imageKey });
  if (rows[0]) background(imageStore().delete(rows[0].key));
  return c.json({ ok: true });
});

const groupCount = async (col: SQL | typeof scans.label, where: SQL[]) => {
  const rows = await db
    .select({ k: sql<string>`${col}`, n: count() })
    .from(scans)
    .where(and(...where))
    .groupBy(sql`1`)
    .orderBy(asc(sql`1`));
  return Object.fromEntries(rows.filter((r) => r.k !== null && r.k !== "").map((r) => [r.k, r.n]));
};

app.get("/api/stats", async (c) => {
  const u = c.get("user");
  const w = dateRange(c, u.id);
  const done = [...w, eq(scans.status, "done")];
  const [{ n }] = await db.select({ n: count() }).from(scans).where(and(...w));
  const [{ a }] = await db.select({ a: avg(scans.confidence) }).from(scans).where(and(...done));
  const recent = await db.select().from(scans).where(and(...w)).orderBy(desc(scans.id)).limit(6);
  return c.json({
    total: n,
    avg_confidence: a ? Math.round(Number(a) * 10) / 10 : null,
    by_label: await groupCount(scans.label, done),
    by_type: await groupCount(scans.scanType as any, w),
    by_status: await groupCount(scans.status as any, w),
    monthly: await groupCount(sql`to_char(${scans.createdAt}, 'YYYY-MM')`, w),
    recent: recent.map(toScan),
  });
});

app.get("/api/insights", async (c) => {
  const u = c.get("user");
  const w = [eq(scans.userId, u.id)];
  const done = [...w, eq(scans.status, "done")];
  const [agg] = await db
    .select({ n: count(), conf: avg(scans.confidence), ms: avg(scans.durationMs) })
    .from(scans)
    .where(and(...done));
  const buckets = await groupCount(
    sql`CASE WHEN ${scans.confidence} >= 90 THEN '90-100%' WHEN ${scans.confidence} >= 80 THEN '80-89%' WHEN ${scans.confidence} >= 70 THEN '70-79%' WHEN ${scans.confidence} >= 60 THEN '60-69%' ELSE 'Below 60%' END`,
    done,
  );
  const byTypeLabel = await db
    .select({ type: scans.scanType, label: scans.label, n: count() })
    .from(scans)
    .where(and(...done))
    .groupBy(scans.scanType, scans.label);
  const models = await groupCount(scans.model as any, done);
  return c.json({
    model: VISION_MODEL,
    analyzed: agg.n,
    avg_confidence: agg.conf ? Math.round(Number(agg.conf) * 10) / 10 : null,
    avg_seconds: agg.ms ? Math.round(Number(agg.ms) / 100) / 10 : null,
    by_status: await groupCount(scans.status as any, w),
    confidence_buckets: buckets,
    quality: await groupCount(sql`${scans.details}->>'imageQuality'`, done),
    body_parts: await groupCount(sql`initcap(${scans.details}->>'bodyPart')`, done),
    by_type_label: byTypeLabel,
    models,
  });
});

// ---------- patients ----------
app.get("/api/patients", async (c) => {
  const u = c.get("user");
  const q = `%${(c.req.query("q") || "").trim()}%`;
  const rows = await db
    .select()
    .from(patients)
    .where(and(eq(patients.userId, u.id), or(ilike(patients.name, q), ilike(patients.pid, q))))
    .orderBy(desc(patients.id));
  const pids = rows.map((r) => r.pid);
  const counts = pids.length
    ? await db
        .select({ pid: scans.patientId, n: count() })
        .from(scans)
        .where(and(eq(scans.userId, u.id), inArray(scans.patientId, pids)))
        .groupBy(scans.patientId)
    : [];
  const cm = Object.fromEntries(counts.map((r) => [r.pid, r.n]));
  return c.json({
    items: rows.map((p) => ({ id: p.id, pid: p.pid, name: p.name, age: p.age, sex: p.sex, notes: p.notes, scans: cm[p.pid] || 0 })),
  });
});

const ageOf = (v: unknown) => {
  const n = parseInt(String(v ?? ""));
  return Number.isFinite(n) && n >= 0 && n <= 130 ? n : null;
};

app.post("/api/patients", async (c) => {
  const u = c.get("user");
  const d = await body(c);
  const pid = String(d.pid || "").trim().slice(0, 64), name = String(d.name || "").trim().slice(0, 120);
  if (!pid || !name) return err(c, "Patient ID and name are required");
  const exists = await db.select({ id: patients.id }).from(patients).where(and(eq(patients.userId, u.id), eq(patients.pid, pid))).limit(1);
  if (exists.length) return err(c, "Patient ID already exists", 409);
  await db.insert(patients).values({
    userId: u.id, pid, name, age: ageOf(d.age), sex: String(d.sex || "").slice(0, 20), notes: String(d.notes || "").slice(0, 2000),
  });
  return c.json({ ok: true }, 201);
});

app.put("/api/patients/:id", async (c) => {
  const u = c.get("user");
  const d = await body(c);
  const name = String(d.name || "").trim().slice(0, 120);
  if (!name) return err(c, "Name is required");
  await db
    .update(patients)
    .set({ name, age: ageOf(d.age), sex: String(d.sex || "").slice(0, 20), notes: String(d.notes || "").slice(0, 2000) })
    .where(and(eq(patients.id, parseInt(c.req.param("id"))), eq(patients.userId, u.id)));
  return c.json({ ok: true });
});

app.delete("/api/patients/:id", async (c) => {
  const u = c.get("user");
  await db.delete(patients).where(and(eq(patients.id, parseInt(c.req.param("id"))), eq(patients.userId, u.id)));
  return c.json({ ok: true });
});

// ---------- support ----------
app.post("/api/support", async (c) => {
  const u = c.get("user");
  const d = await body(c);
  const message = String(d.message || "").trim();
  if (!message) return err(c, "Message is required");
  await db.insert(supportMessages).values({
    userId: u.id,
    kind: String(d.kind || "Support").slice(0, 40),
    subject: String(d.subject || "").slice(0, 200),
    message: message.slice(0, 5000),
  });
  return c.json({ ok: true });
});

app.all("/api/*", (c) => err(c, "Not found", 404));

// ---------- uploaded images (source for the Netlify Image CDN) ----------
app.get("/uploads/:key", async (c) => {
  const key = c.req.param("key");
  if (!KEY_RE.test(key)) return c.text("Not found", 404);
  const r = await imageStore().getWithMetadata(key, { type: "arrayBuffer" });
  if (!r) return c.text("Not found", 404);
  return new Response(r.data as ArrayBuffer, {
    headers: {
      "Content-Type": String(r.metadata?.contentType || "image/jpeg"),
      "Cache-Control": "public, max-age=31536000, immutable",
      "X-Robots-Tag": "noindex",
    },
  });
});

export default app;

export const config = {
  path: ["/api/*", "/uploads/*"],
};

package-lock.json
added
+2229
Load change
Large changes are not rendered by default.


package.json
added
+20
{
  "name": "medivision-ai",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "netlify dev --port 8889",
    "db:generate": "drizzle-kit generate"
  },
  "dependencies": {
    "@google/genai": "^3.4.0",
    "@netlify/blobs": "^11.1.9",
    "@netlify/database": "^2.0.3",
    "@netlify/server": "^0.1.6",
    "drizzle-orm": "^1.0.0-beta.22",
    "hono": "^4.13.19"
  },
  "devDependencies": {
    "drizzle-kit": "^1.0.0-beta.22"
  }
}

public/analytics.html
added
+15
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Analytics - MediVision AI</title><link rel="stylesheet" href="css/style.css"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script></head>
<body class="bg"><script src="js/app.js"></script><script>navbar("analytics")</script>
<main class="wrap"><h1>Analytics</h1><br><div class="row"><label>From</label><input id="f" type="date"><label>To</label><input id="to" type="date"></div>
<div class="grid" id="sum"></div><br>
<div class="grid"><div class="card"><h2>Monthly scan activity</h2><canvas id="c1" height="220"></canvas></div><div class="card"><h2>Normal vs abnormal</h2><canvas id="c2" height="220"></canvas></div><div class="card"><h2>Image category</h2><canvas id="c3" height="220"></canvas></div></div></main>
<script>
async function load(){const s=await api("/stats?from="+f.value+"&to="+to.value);
 const n=k=>s.by_label[k]||0,cl=n("Normal")+n("Abnormal"),ab=cl?Math.round(100*n("Abnormal")/cl):0;
 sum.innerHTML=[["Total scans",s.total],["Classified",cl],["Normal",n("Normal")],["Abnormal",n("Abnormal")],["Abnormal rate",ab+"%"]].map(([a,b])=>`<div class="card stat"><b>${b}</b><span>${a}</span></div>`).join("");
 chart("c1",{type:"bar",data:{labels:Object.keys(s.monthly),datasets:[{label:"Scans",data:Object.values(s.monthly),backgroundColor:"#42D9E8"}]}});
 chart("c2",{type:"doughnut",data:{labels:Object.keys(s.by_label),datasets:[{data:Object.values(s.by_label),backgroundColor:Object.keys(s.by_label).map(k=>k==="Abnormal"?"#dc2626":"#16a34a")}]}});
 chart("c3",{type:"pie",data:{labels:Object.keys(s.by_type),datasets:[{data:Object.values(s.by_type),backgroundColor:COLORS}]}})}
f.onchange=to.onchange=load;load().catch(e=>toast(e.message,true));
</script></body></html>

public/classification.html
added
+21
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Classification - MediVision AI</title><link rel="stylesheet" href="css/style.css"></head>
<body class="bg"><script src="js/app.js"></script><script>navbar("classification")</script>
<main class="wrap"><h1>Prediction Result</h1><div id="out"></div></main>
<script>
function render(r){
 if(!r){out.innerHTML='<p class="sub">Open a scan from History, or upload a new image.</p><a class="btn" href="upload.html">Upload an image</a>';return}
 if(!scanReady(r,out,render))return;
 const d=r.details||{},bad=r.label==="Abnormal";
 const bars=Object.entries(r.probabilities).map(([k,v])=>`<p>${esc(k)}: ${v}%</p><div class="bar"><i data-w="${v}"></i></div>`).join("");
 const lvl=r.confidence>=85?"High":r.confidence>=65?"Moderate":"Low";
 out.innerHTML=`<div class="grid"><div class="card"><img class="pv" src="${r.original}" alt="Uploaded ${esc(r.scan_type)}"></div><div class="card">
 <span class="pill ${esc(r.label)}">${bad?"⚠ ":"✓ "}${esc(r.label)}</span><h2 style="margin-top:16px">Confidence ${r.confidence}% <small class="warn">(${lvl})</small></h2>${bars}
 <dl class="kv"><dt>Scan type</dt><dd>${esc(r.scan_type)}${d.modalityDetected?` · detected: ${esc(d.modalityDetected)}`:""}</dd>${d.bodyPart?`<dt>Body region</dt><dd>${esc(d.bodyPart)}</dd>`:""}${d.imageQuality?`<dt>Image quality</dt><dd>${esc(d.imageQuality)}</dd>`:""}<dt>Patient</dt><dd>${esc(r.patient_id)||"not linked"}</dd><dt>Analyzed</dt><dd>${esc(r.created)} UTC · ${(r.duration_ms/1000).toFixed(1)}s</dd></dl>
 ${d.impression?`<p><b>Impression:</b> ${esc(d.impression)}</p>`:""}
 <p class="warn"><b>Medical disclaimer:</b> ${esc(r.disclaimer)} A qualified clinician must review every result.</p></div></div><br>
 <div class="card"><h2>Findings</h2><p>${esc(r.findings)}</p>${(d.recommendations||[]).length?`<h3 style="margin-top:14px">Suggested next steps</h3><ul>${d.recommendations.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}</div><br>
 <a class="btn" href="explainable-ai.html?id=${r.id}">View Explanation →</a> <a class="btn ghost" href="report.html?id=${r.id}">Open Report</a> <a class="btn ghost" href="upload.html">Analyze Another</a>`;
 setTimeout(()=>document.querySelectorAll(".bar i").forEach(b=>b.style.width=b.dataset.w+"%"),50)}
loadScan().then(render).catch(e=>toast(e.message,true));
</script></body></html>

public/css/style.css
added
+93

public/dashboard.html
added
+18
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard - MediVision AI</title><link rel="stylesheet" href="css/style.css"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script></head>
<body class="bg"><script src="js/app.js"></script><script>navbar("dashboard")</script>
<main class="wrap"><h1 id="hi">Welcome</h1><p class="sub">Your scan activity at a glance.</p>
<div class="grid" id="stats"></div>
<div class="grid" style="margin-top:22px"><div class="card"><h2>Classification distribution</h2><canvas id="c1" height="200"></canvas></div><div class="card"><h2>Notifications</h2><div id="notes"></div></div></div>
<h2 style="margin:26px 0 12px">Recent scans</h2><div class="thumbs" id="recent"></div><br><a class="btn" href="upload.html">+ Quick upload</a></main>
<script>
hi.textContent="Welcome, "+(localStorage.getItem("mv_name")||"clinician");
(async()=>{
 const s=await api("/stats");
 const n=k=>s.by_label[k]||0;
 stats.innerHTML=[["Total scans",s.total],["Classified Normal",n("Normal")],["Classified Abnormal",n("Abnormal")],["Average confidence",s.avg_confidence!=null?s.avg_confidence+"%":"–"]].map(([a,b])=>`<div class="card stat"><b>${b}</b><span>${a}</span></div>`).join("");
 chart("c1",{type:"doughnut",data:{labels:Object.keys(s.by_label),datasets:[{data:Object.values(s.by_label),backgroundColor:Object.keys(s.by_label).map(k=>k==="Abnormal"?"#dc2626":"#16a34a")}]}});
 notes.innerHTML=(s.recent.map(r=>`<p class="warn"><a href="classification.html?id=${r.id}">Scan #${r.id}</a> ${r.status==="done"?`classified <b>${esc(r.label)}</b> (${r.confidence}%)`:r.status==="processing"?"is being analyzed…":r.status==="rejected"?"was not accepted (not a medical image)":"needs a retry"} · ${esc(r.created)}</p>`).join("")||'<p class="warn">No activity yet.</p>');
 recent.innerHTML=s.recent.map(r=>`<div class="card" onclick="location.href='classification.html?id=${r.id}'"><img src="${r.thumb}" alt="Scan ${r.id}" loading="lazy"><p>${statusPill(r)}</p><p class="warn">${esc(r.scan_type)} · ${esc(r.created)}</p></div>`).join("")||'<p class="warn">Upload your first scan.</p>';
})();
</script></body></html>

public/explainable-ai.html
added
+22
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Explainable AI - MediVision AI</title><link rel="stylesheet" href="css/style.css"></head>
<body class="bg"><script src="js/app.js"></script><script>navbar("explainable-ai")</script>
<main class="wrap"><h1>Explainable AI</h1><p class="sub">Attention map: warm colours (red/yellow) mark the regions that influenced the AI most.</p><div id="out"></div></main>
<script>
async function render(r){
 if(!r){out.innerHTML='<a class="btn" href="history.html">Pick a scan from History</a>';return}
 if(!scanReady(r,out,render))return;
 const lvl=r.confidence>=85?"high":r.confidence>=65?"moderate":"low";
 out.innerHTML=`<div class="grid"><div class="card"><h2>Original</h2><img class="pv" src="${r.original}" alt="Original scan"></div>
 <div class="card"><h2>Attention overlay</h2><div class="cmp"><img src="${r.original}" alt="Scan with heatmap"><img class="top" id="hm" alt="" style="opacity:.75"></div>
 <p class="warn">Heatmap opacity (slide to compare with the original)</p><input type="range" min="0" max="100" value="75" oninput="document.getElementById('hm').style.opacity=this.value/100"></div></div><br>
 <div class="grid"><div class="card"><h2>Why this prediction?</h2><p>Prediction: <span class="pill ${esc(r.label)}">${esc(r.label)}</span> at ${r.confidence}% (${lvl} confidence).</p>
 <p style="margin-top:12px">${esc(r.findings)}</p>
 ${(r.details?.differentials||[]).length?`<h3 style="margin-top:14px">Possible explanations</h3><ul>${r.details.differentials.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:""}
 <p class="warn">Red/yellow areas pushed the AI toward this output. Check whether they fall on anatomically relevant regions; if they sit on text markers, borders or equipment, treat the prediction with suspicion. ${lvl==="low"?"<b>Low confidence: seek clinician review.</b>":""}</p>
 <p class="warn">${esc(r.disclaimer)}</p></div>
 <div class="card"><h2>Regions of influence</h2>${regionList(r)}</div></div><br>
 <a class="btn ghost" href="classification.html?id=${r.id}">← Back</a> <a class="btn" href="report.html?id=${r.id}">Open Report →</a>`;
 hm.src=await heatmapURL(r)}
loadScan().then(render).catch(e=>toast(e.message,true));
</script></body></html>

public/gallery.html
added
+22
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gallery - MediVision AI</title><link rel="stylesheet" href="css/style.css"></head>
<body class="bg"><script src="js/app.js"></script><script>navbar("gallery")</script>
<main class="wrap"><h1>Medical Image Gallery</h1><br>
<div class="row"><input id="q" placeholder="Search patient ID / result"><select id="t"><option value="">All categories</option><option>X-Ray</option><option>CT Scan</option><option>MRI</option></select><button class="btn ghost sm" id="vw">List view</button></div>
<div class="thumbs" id="g"></div></main>
<div class="modal" id="zm"><div class="card" style="max-width:720px"><h2>Scan <span id="zi"></span></h2>
<div class="cmp"><img id="za"><img class="top" id="zb" style="opacity:0"></div>
<p class="warn">Before / after: slide to blend the AI attention overlay over the original</p><input type="range" min="0" max="100" value="0" id="zs">
<p class="warn" id="zmeta"></p><button class="btn ghost" onclick="modal('zm',false)">Close</button></div></div>
<script>
let list=false;
async function load(){const d=await api("/scans?per=48&type="+encodeURIComponent(t.value)+"&q="+encodeURIComponent(q.value));
 g.className="thumbs"+(list?" list":"");
 g.innerHTML=d.items.map(r=>`<div class="card" onclick="zoom(${r.id})"><img src="${r.thumb}" alt="Scan ${r.id}" loading="lazy"><p><b>${esc(r.scan_type)}</b> <span style="font-size:.75rem">${statusPill(r).replace('class="pill','style="padding:2px 10px" class="pill')}</span></p><p class="warn" style="margin-top:4px">#${r.id} · ${esc(r.patient_id)||"no patient"} · ${esc(r.created)}</p></div>`).join("")||'<p class="sub">No images yet.</p>'}
q.oninput=t.onchange=load;vw.onclick=()=>{list=!list;vw.textContent=list?"Grid view":"List view";load()};
async function zoom(i){const r=await api("/scans/"+i);zi.textContent="#"+i;za.src=r.original;zb.removeAttribute("src");zs.value=0;zb.style.opacity=0;
 zmeta.innerHTML=`${esc(r.scan_type)} · ${r.status==="done"?esc(r.label)+" "+r.confidence+"%":esc(r.status)} · patient ${esc(r.patient_id)||"n/a"} · ${esc(r.created)} · <a href="classification.html?id=${r.id}">Open result →</a>`;modal("zm",true);
 if(r.status==="done")zb.src=await heatmapURL(r)}
zs.oninput=()=>zb.style.opacity=zs.value/100;
load().catch(e=>toast(e.message,true));
</script></body></html>


