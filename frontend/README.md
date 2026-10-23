# DataScout Frontend

> **Next.js 14 AI Chat Interface**  
> Version 1.0.0 | Production Ready

[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Modern, responsive frontend for DataScout Enterprise Platform with real-time AI chat, analytics dashboard, and dynamic visualizations.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running

### Installation

```bash
# Clone repository
git clone https://github.com/MBilalKhanAI/DataScout-frontend.git
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local and set API URL

# Run development server
npm run dev
```

**App will be available at:** http://localhost:3000

---

## 🌟 Features

### 📊 **Real-Time Chat Interface**
- Multi-agent AI responses
- Markdown rendering
- Thought visualization
- Dynamic chart rendering

### 📈 **Analytics Dashboard**
- Live performance metrics
- Query success rate
- Agent performance breakdown
- Recent activity tracking

### 🎨 **Theme Switching**
- Dark mode
- Light mode
- Auto mode (system preference)

### 📝 **Query Management**
- History tracking
- Quick templates
- Result previews

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js Pages (App Router)
│   │   ├── (main)/              # Main layout group
│   │   │   ├── analytics/       # Analytics page
│   │   │   ├── query/           # Chat + history page
│   │   │   ├── settings/        # Settings page
│   │   │   ├── documents/       # Documents page
│   │   │   ├── agents/          # Agents page
│   │   │   └── collaborate/     # Collaborate page
│   │   └── layout.tsx           # Root layout
│   │
│   ├── components/               # React Components
│   │   ├── ChatInterface.tsx    # Main chat component
│   │   ├── DynamicChart.tsx     # Chart visualization
│   │   ├── sidebar.tsx          # Navigation
│   │   └── ui/                  # shadcn/ui components
│   │
│   └── lib/                      # Utilities
│       ├── api.ts               # API functions (consolidated)
│       └── utils.ts             # Helper functions
│
├── public/                       # Static assets
├── .env.example                 # Environment template
├── package.json                 # Dependencies
├── tsconfig.json                # TypeScript config
└── tailwind.config.ts           # Tailwind CSS config
```

---

## 🔧 Configuration

Create `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production:
```env
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

---

## 🎨 Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **Charts:** Recharts
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Notifications:** Sonner

---

## 📦 Key Components

### ChatInterface
Main chat component with agent routing and visualization.

```typescript
import { ChatInterface } from '@/components/ChatInterface';

<ChatInterface />
```

### DynamicChart
Renders bar, line, pie, and area charts.

```typescript
import { DynamicChart } from '@/components/DynamicChart';

<DynamicChart config={chartConfig} />
```

### API Functions
Consolidated API calls in `lib/api.ts`:

```typescript
import { sendChatMessage, fetchAnalyticsSummary } from '@/lib/api';

// Send chat message
const response = await sendChatMessage("Show sales by region");

// Get analytics
const analytics = await fetchAnalyticsSummary();
```

---

## 🧪 Development

### Run Development Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
npm start
```

### Lint
```bash
npm run lint
```

### Type Check
```bash
npx tsc --noEmit
```

---

## 🚢 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Add environment variable
vercel env add NEXT_PUBLIC_API_URL
```

### Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

CMD ["npm", "start"]
```

### Static Export

```bash
# Add to next.config.js
output: 'export'

# Build
npm run build

# Deploy 'out' directory
```

---

## 📱 Pages

| Page | Route | Description |
|------|-------|-------------|
| Chat | `/query` | Main chat interface with history |
| Analytics | `/analytics` | Performance dashboard |
| Documents | `/documents` | PDF upload and management |
| Agents | `/agents` | Agent execution and custom agents |
| Settings | `/settings` | User preferences |
| Collaborate | `/collaborate` | Workspace management (UI only) |

---

## 🎯 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

---

## 🔗 Backend Integration

**Backend Repo:** [DataScout-backend](https://github.com/MBilalKhanAI/DataScout-backend)

**API Endpoints Used:**
- `POST /chat` - Main chat
- `GET /api/analytics/summary` - Analytics data
- `GET /api/history` - Query history
- `GET/POST /api/settings` - User settings
- `POST /api/documents/upload` - Document upload

---

## 🎨 Customization

### Colors
Edit `tailwind.config.ts`:

```typescript
theme: {
  extend: {
    colors: {
      primary: {...},
      secondary: {...}
    }
  }
}
```

### Add New Page

```bash
# Create page
mkdir src/app/(main)/newpage
touch src/app/(main)/newpage/page.tsx

# Add to sidebar
# Edit src/components/sidebar.tsx
```

---

## 📊 Performance

- **Lighthouse Score:** 95+
- **First Contentful Paint:** <1s
- **Time to Interactive:** <2s
- **Bundle Size:** ~200KB gzipped

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

## 📧 Contact

- **Email:** drmbilal172@gmail.com
- **GitHub:** [@MBilalKhanAI](https://github.com/MBilalKhanAI)
- **LinkedIn:** [Muhammad Bilal Khan](https://www.linkedin.com/in/muhammad-bilal-khan-885ai654)

---

**Built with Next.js, TypeScript, and Tailwind CSS**
