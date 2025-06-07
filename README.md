
```markdown

# Taxonomy Audit & Governance Helper (Web Edition)

Zero-install web tool for Amplitude CS Architects  
→ **Upload 3 CSV exports → Audit → Recommend → (optional) Generate bulk-fix file**

---

## 1. Quick Start (Dev)

```bash
npm i          # installs React, Vite, Tailwind, shadcn/ui
npm run dev    # Vite dev server → http://localhost:5173
```

---

## 2. Running an Audit

1. **Create Project** → name = client org.

2. **Upload 3 files**:

   | File                              | Where to export in Amplitude                  |
   | --------------------------------- | --------------------------------------------- |
   | Event & Event-Property schema CSV | _Govern &gt; Export CSV_ (per project)        |
   | User-Property schema CSV          | _Govern &gt; User Properties &gt; Export CSV_ |
   | Org Usage Report CSV              | _Settings &gt; Usage Reports &gt; Download_   |

3. Click **Start Audit** → processing occurs **in-browser** (no server IO).

4. After spinner completes: view issue summary, download **PDF** & **Evidence Excel**.

---

## 3. Generating Fixes

1. Click **Generate Fix File**.

2. Review table (see _Appendix A - Data Specs – Reviewable-CSV schema_).

3. Mark `Approve = Y` where desired → **Download Approved CSV**.

4. (Fast-follow) Import CSV via Amplitude UI **or** send JSON body via Taxonomy API.

---

## 4. Governance Toolkit (optional)

_7-question wizard_ → builds ZIP of static templates (placeholder docs for now) from `/public/governance-templates/`.\
Placeholders replaced:

```plaintext
text
{{CLIENT_NAME}}, {{TEAM_SIZE}}, {{PRIMARY_PAINPOINT}}
```

---

## 5. Tech Stack

| Layer    | Choice                                                                |
| -------- | --------------------------------------------------------------------- |
| Frontend | React + Vite + Tailwind + shadcn/ui                                   |
| Auth v0  | Unlisted URL + passphrase (`VITE_APP_PASSPHRASE`)                     |
| Auth v1  | Supabase Auth – Google provider (`allowed_domains=['amplitude.com']`) |
| PDF      | `jspdf`                                                               |
| Excel    | `xlsx`                                                                |
| Parsing  | `papaparse` in Web Worker                                             |

---

## 6. Folder Structure

```plaintext
pgsql
src/
  components/
  pages/
    Dashboard.tsx
    Project.tsx
  logic/
    audit.ts      # pure functions: 3 CSV blobs → results JSON
    pdf.ts
    fixfile.ts
public/
  governance-templates/
docs/
  Appendix_A_Data_Specs.md
```

---

## 7. Appendix

See **docs/Appendix_A_Data_Specs.md** for detailed column lists and fix-file schema.
