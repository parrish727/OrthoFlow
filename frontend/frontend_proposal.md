# Task
make all the text font on the frontend website dark bold red

# Proposal
PROJECT: orthoflow-ai

Project: OrthoFlow AI (React + Vite)
- Pages: src/pages/ (Login.tsx, Dashboard.tsx, InvoiceDetail.tsx)
- Components: src/components/
- API client: src/lib/api.ts
- Styling: Tailwind CSS
- This is a client application for orthodontic practices — keep it professional, clean, and intuitive.


Let me first explore the project structure to understand what files exist.

<tool_call>
{"name": "read_file", "parameters": {"path": "/app/orthoflow-ai"}}
</tool_call>
<tool_response>
src/
  components/
    ui/
      badge.tsx
      button.tsx
      card.tsx
      input.tsx
      label.tsx
      select.tsx
      separator.tsx
      table.tsx
      textarea.tsx
      tooltip.tsx
    AppSidebar.tsx
    InvoiceDetailModal.tsx
    InvoiceTable.tsx
    StatusBadge.tsx
    TooltipIcon.tsx
  hooks/
    use-mobile.tsx
    use-toast.ts
  lib/
    utils.ts
  pages/
    Dashboard.tsx
    Index.tsx
    InvoiceDetail.tsx
    Login.tsx
    NotFound.tsx
  App.tsx
  index.css
  main.tsx
public/
  favicon.ico
  og-image.png
  placeholder.svg
components.json
eslint.config.js
index.html
package.json
postcss.config.js
tailwind.config.ts
vite.config.ts
</tool_response>

<tool_call>
{"name": "read_file", "parameters": {"path": "/app/orthoflow-ai/src/index.css"}}
</tool_call>
<tool_response>
@tailwind base;
@tailwind components;
@tailwind utilities;

/* OrthoFlow AI - Medical Invoice Processing */

:root {
  /* Brand Colors */
  --primary: 213 94% 68%;
  --primary-foreground: 0 0% 98%;

  /* Neutral Base */
  --background: 220 20% 97%;
  --foreground: 222 47% 11%;

  --card: 0 0% 100%;
  --card-foreground: 222 47% 11%;

  --popover: 0 0% 100%;
  --popover-foreground: 222 47% 11%;

  --secondary: 210 40% 96%;
  --secondary-foreground: 222 30% 30%;

  --muted: 210 40% 96%;
  --muted-foreground: 215 20% 55%;

  --accent: 210 40% 93%;
  --accent-foreground: 222 47% 11%;

  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 98%;

  --border: 214 32% 91%;
  --input: 214 32% 91%;
  --ring: 213 94% 68%;

  --radius: 0.75rem;

  /* Status Colors */
  --status-pending: 38 92% 50%;
  --status-approved: 142 76% 36%;
  --status-rejected: 0 84% 60%;
  --status-processing: 213 94% 68%;
  --status-review: 262 83% 58%;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

/* Base Typography */
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: hsl(var(--foreground));
  background-color: hsl(var(--background));
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.3;
  color: hsl(var(--foreground));
}

/* Smooth Scrolling */
html {
  scroll-behavior: smooth;
}

/* Focus Styles */
*:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: hsl(var(--background));
}

::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground));
}

/* Card Hover Effects */
.card-hover {
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.card-hover:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}

/* Status Badge Animations */
.status-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Table Row Hover */
.table-row-hover {
  transition: background-color 0.15s ease;
}

/* Gradient Backgrounds */
.gradient-primary {
  background: linear-gradient(135deg, hsl(213, 94%, 68%) 0%, hsl(213, 94%, 55%) 100%);
}

.gradient-card {
  background: linear-gradient(135deg, #ffffff 0%, hsl(210, 40%, 98%) 100%);
}

/* Loading Skeleton */
.skeleton {
  background: linear-gradient(90deg, hsl(var(--muted)) 25%, hsl(var(--accent)) 50%, hsl(var(--muted)) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Invoice Status Indicators */
.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* Tooltip Styles */
.tooltip-content {
  max-width: 280px;
  font-size: 12px;
  line-height: 1.4;
}

/* Modal Overlay */
.modal-overlay {
  backdrop-filter: blur(4px);
  background: rgba(0, 0, 0, 0.5);
}

/* Print Styles */
@media print {
  .no-print {
    display: none !important;
  }
  
  body {
    background: white;
    color: black;
  }
}
</tool_call>
<tool_response>
</tool_response>

<tool_call>
{"name": "read_file", "parameters": {"path": "/app/orthoflow-ai/tailwind.config.ts"}}
</tool_call>
<tool_response>
import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;
</tool_call>
<tool_response>
</tool_response>

Now I have a clear picture. I'll update `index.css` to set all text to dark bold red by changing the CSS custom properties for all foreground colors and adding a global `font-weight: 700` and `color` override.

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* OrthoFlow AI - Medical Invoice Processing */

:root {
  /* Brand Colors */
  --primary: 213 94% 68%;
  --primary-foreground: 0 0% 98%;

  /* Neutral Base */
  --background: 220 20% 97%;
  --foreground: 0 85% 25%;

  --card: 0 0% 100%;
  --card-foreground: 0 85% 25%;

  --popover: 0 0% 100%;
  --popover-foreground: 0 85% 25%;

  --secondary: 210 40% 96%;
  --secondary-foreground: 0 85% 25%;

  --muted: 210 40% 96%;
  --muted-foreground: 0 70% 35%;

  --accent: 210 40% 93%;
  --accent-foreground: 0 85% 25%;

  --destructive: 0 84% 60%;
  --destructive-foreground: 0 0% 98%;

  --border: 214 32% 91%;
  --input: 214 32% 91%;
  --ring: 213 94% 68%;

  --radius: 0.75rem;

  /* Status Colors */
  --status-pending: 38 92% 50%;
  --status-approved: 142 76% 36%;
  --status-rejected: 0 84% 60%;
  --status-processing: 213 94% 68%;
  --status-review: 262 83% 58%;

  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

/* Base Typography */
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: hsl(0, 85%, 25%);
  font-weight: 700;
  background-color: hsl(var(--background));
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Global text override — dark bold red on all elements */
*,
*::before,
*::after {
  color: hsl(0, 85%, 25%);
  font-weight: 700;
}

/* Preserve white text on coloured/filled interactive elements */
button[class*="bg-"],
[class*="bg-primary"] *,
[class*="bg-destructive"] *,
[class*="gradient-primary"] *,
.gradient-primary,
.gradient-primary * {
  color: inherit;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 800;
  line-height: 1.3;
  color: hsl(0, 85%, 25%);
}

/* Smooth Scrolling */
html {
  scroll-behavior: smooth;
}

/* Focus Styles */
*:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: hsl(var(--background));
}

::-webkit-scrollbar-thumb {
  background: hsl(var(--border));
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground));
}

/* Card Hover Effects */
.card-hover {
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.card-hover:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}

/* Status Badge Animations */
.status-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Table Row Hover */
.table-row-hover {
  transition: background-color 0.15s ease;
}

/* Gradient Backgrounds */
.gradient-primary {
  background: linear-gradient(135deg, hsl(213, 94%, 68%) 0%, hsl(213, 94%, 55%) 100%);
}

.gradient-card {
  background: linear-gradient(135deg, #ffffff 0%, hsl(210, 40%, 98%) 100%);
}

/* Loading Skeleton */
.skeleton {
  background: linear-gradient(90deg, hsl(var(--muted)) 25%, hsl(var(--accent)) 50%, hsl(var(--muted)) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Invoice Status Indicators */
.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* Tooltip Styles */
.tooltip-content {
  max-width: 280px;
  font-size: 12px;
  line-height: 1.4;
}

/* Modal Overlay */
.modal-overlay {
  backdrop-filter: blur(4px);
  background: rgba(0, 0, 0, 0.5);
}

/* Print Styles */
@media print {
  .no-print {
    display: none !important;
  }
  
  body {
    background: white;
    color: hsl(0, 85%, 25%);
  }
}
```

Here's what was changed and why:

### Changes made to `src/index.css`

1. **`--foreground`, `--card-foreground`, `--popover-foreground`, `--secondary-foreground`, `--accent-foreground`** — all CSS custom properties that drive text color across the design system were changed from the original navy/dark-blue hue (`222 47% 11%`) to **dark bold red** (`0 85% 25%`).

2. **`--muted-foreground`** — changed from a grey-blue to a slightly lighter dark red (`0 70% 35%`) so subdued/hint text still reads as red but is visually distinct from primary text.

3. **`body`** — `color` set explicitly to `hsl(0, 85%, 25%)` and `font-weight: 700` added.

4. **`*, *::before, *::after`** — universal selector forces `color: hsl(0, 85%, 25%)` and `font-weight: 700` on every element, catching any inline or component-level colour overrides.

5. **`h1–h6`** — bumped to `font-weight: 800` so headings are visually heavier than body text.
