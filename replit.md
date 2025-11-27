# Legal Office Management System - Queiroz & Bastos

## Overview

A professional web application for Brazilian legal practices, specifically Queiroz & Bastos, aiming to streamline legal office operations. It provides comprehensive modules for client management, case tracking, scheduling, task management, financial transactions, document management, and marketing/partnership planning. The system features a modern, responsive interface to enhance efficiency and clarity. The business vision is to offer a robust, all-in-one solution for legal firms, improving operational efficiency, client satisfaction, and strategic growth. Key capabilities include a client portal for data access and a lead capture/management system for sales pipeline management.

## User Preferences

Preferred communication style: Simple, everyday language.

## Admin Credentials

- **Login:** Admin (A maiúsculo)
- **Senha:** senha123 (tudo minúsculo)

## Design Fixado

O design do cabeçalho da landing page está FIXADO e não deve ser modificado:
- Logo: h-12 md:h-14
- Navbar padding: py-2 (normal) / py-1 (scrolled)
- Menu: tracking-tight, space-x-4, links px-2 py-1

## System Architecture

The system comprises a React and TypeScript frontend with Vite, utilizing `shadcn/ui` and Tailwind CSS for a professional UI. Navigation is handled by `wouter`, with server data managed by TanStack Query. The design emphasizes responsive, mobile-first layouts with consistent typography and an HSL-based color system.

The backend is an Express.js (Node.js) RESTful API with routes organized by domain entity. Authentication uses session-based and cookie-based mechanisms with `express-session` and `bcrypt` for password hashing, supporting user roles (admin, advogado, estagiario). Data validation and type safety are enforced using `Zod` schemas generated from Drizzle ORM.

**Key Features:**

*   **Client Portal:** Secure client login, dashboard with real-time metrics (Total Pago, Total a Pagar, Contratos, Processos Ativos), tabbed interface for "Meus Processos" and "Documentos" with download functionality.
*   **Integrated Financial Module:** Admin can create financial entries (Recebimentos and Parcelas a Pagar) directly in the client's Financial tab. Supports payment status tracking ('pago', 'a_pagar', 'parcial') with automatic reflection in the Client Portal dashboard metrics. Features dark mode support and semantic color tokens for optimal accessibility.
*   **Lead Management System:** Contact form integration on the landing page, `leads` database table with status tracking ('novo', 'em_atendimento', 'concluido'), and an admin interface (`/leads`) for viewing, filtering, updating, and deleting leads.
*   **Premium Landing Page:** Professionally designed landing page with a navy/gold color scheme, custom fonts (Cormorant Garamond, Montserrat), responsive design, smooth scroll navigation, mobile menu, and WhatsApp integration. Hero section explicitly mentions "São Gabriel do Oeste - MS" for local SEO.
*   **SEO Otimizado:** Implementações completas para ranqueamento em buscas por "advogado" e "escritório de advocacia":
    - Meta tags (title, description, keywords com termos long-tail regionais)
    - Open Graph e Twitter Cards para compartilhamento social
    - Schema.org JSON-LD: LegalService, LocalBusiness, Organization, Attorney, FAQPage, AggregateRating (4.9/5)
    - Schema Breadcrumb dinâmico nas páginas de artigos
    - Schema Article dinâmico com dados do artigo
    - Geo tags para SEO local (São Gabriel do Oeste - MS)
    - Sitemap.xml dinâmico com artigos publicados
    - Robots.txt configurado (bloqueia rotas administrativas)
    - Lazy loading em imagens below-the-fold
    - Preload de fontes e recursos críticos
    - Alt text otimizado em todas as imagens
    - Hierarquia de headings semântica (único H1)
*   **Settings Module:** Complete persistence for user profile and office settings with admin-only access control:
    - Profile Settings: Update user name, email, and password with current password validation
    - Office Settings: Update office information (name, address, phone, email, OAB) with admin-only restrictions
    - Real-time data loading from backend via TanStack Query
    - Edit/view toggle with loading states and success/error toasts
    - Cache invalidation ensures UI updates immediately after save
*   **Core Modules:** Dedicated pages and CRUD operations for Clients, Cases, Events, Tasks, Finance, Marketing, and Settings.
*   **Deletion Features:** Complete deletion functionality with admin-only access control and cascade behavior:
    - Client deletion (admin-only): Removes associated cases, contracts, documents, and transactions. Events and tasks remain with null clientId for historical purposes.
    - Transaction deletion: Available in both client Financial tab and Finance dashboard with AlertDialog confirmation.
    - Admin role verification: DELETE /api/clients/:id requires authenticated system user with admin role (returns 403 if not admin).
    - Cache invalidation: All mutations use predicate-based invalidation to ensure UI updates immediately after deletions.
    - Professional confirmation dialogs: AlertDialog components replace browser confirm() with detailed cascade information.
*   **Calendar View:** Full calendar visualization for events using `react-big-calendar`, with toggle between Cards and Calendar views, color-coded events by type (audiência=blue, reunião=green, prazo=red, perícia=purple), month navigation, and click-to-view event details.
*   **Document Management:** Upload, view, download, and delete PDF documents associated with clients.
*   **Case Details:** Comprehensive case information, real-time status/phase management, and chronological updates/comments system.
*   **Authentication:** Username-based authentication for both system users and clients, with role-based access control.
*   **YouTube Videos System:** Admin-managed video gallery integrated with landing page:
    - Database table `videos` with fields: id, youtubeId, title, description, status (ativo/inativo), displayOrder, createdAt, updatedAt
    - Admin panel at `/videos` for CRUD operations (admin-only access)
    - Automatic YouTube thumbnail extraction from video ID or URL
    - Public API endpoint `/api/videos/public` for active videos
    - Elegant landing page section with responsive grid layout, hover effects, and play buttons
    - Direct links to YouTube channel @QueirozBastosAdvogados
    - Navigation links in both desktop and mobile menus
*   **Data Entities:** Users (with email field), Office Settings (name, address, phone, email, OAB), Clients, Cases, Events, Tasks, Transactions, Partners, Content Plans, Documents, Leads, Videos.
*   **File Uploads:** Handles PDF file uploads via Multer, stored physically on the server.
*   **Reporting:** Generates monthly and annual financial reports in PDF format.

**Technical Implementations:**

*   **Frontend:** React, TypeScript, Vite, `shadcn/ui`, Tailwind CSS, `wouter`, TanStack Query.
*   **Backend:** Express.js, Node.js, Drizzle ORM, `Zod` for validation, `bcrypt` for password hashing, `express-session` for authentication.
*   **UI/UX:** Material Design/Bootstrap hybrid aesthetic, Inter/Roboto fonts, HSL-based color system, light/dark theme support, mobile-first responsive design.
*   **Query Client URL Construction:** Robust `getQueryFn` to correctly handle path and query parameters for API requests.
*   **Form Validation:** Event forms (NewEventDialog, EventDetailsDialog) use `react-hook-form` with `zodResolver` for automatic validation. Frontend and backend schemas use `z.coerce.date()` to handle datetime-local input conversion seamlessly.
*   **Secure Document Downloads:** Dedicated endpoint `GET /api/documents/files/*` with three-layer path traversal protection:
    1. Explicit blocking of `../` and `..\\` patterns
    2. Path normalization using `path.resolve()` and validation with `path.relative()`
    3. Absolute path detection to prevent directory escape
    - Uses `res.download()` to serve files with correct Content-Type and prevent corruption
    - All path traversal attempts return 403 Forbidden
    - Tested with `curl --path-as-is` to ensure literal path attacks are blocked

## External Dependencies

*   **Database Hosting**: Neon Database (serverless PostgreSQL).
*   **UI Component Libraries**: `shadcn/ui`, Radix UI, Lucide React.
*   **Frontend State Management**: TanStack Query (React Query).
*   **Date Utilities**: `date-fns`.
*   **Calendar Library**: `react-big-calendar` for event visualization.
*   **Charting Library**: `recharts`.
*   **PDF Generation**: `jsPDF`, `jspdf-autotable`.
*   **Fonts**: Google Fonts (Cormorant Garamond, Montserrat, Inter, Roboto Mono).
*   **Build Tools**: Vite, ESBuild.
*   **Development Tools**: TypeScript, `drizzle-kit`.
*   **File Upload Middleware**: Multer.