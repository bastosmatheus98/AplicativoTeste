# Design Guidelines: Legal Office Management System

## Design Approach
**Selected Approach:** Design System - Material Design/Bootstrap Hybrid
**Rationale:** This is a utility-focused, data-intensive professional application requiring efficiency, clarity, and consistency. The legal office context demands a trustworthy, professional aesthetic with excellent form and table design.

**Key Principles:**
- Clarity over decoration
- Efficiency in data presentation
- Professional legal office aesthetic
- Consistent interaction patterns

---

## Typography System

**Font Families:**
- Primary: Inter or Roboto (via Google Fonts)
- Headings: Same as primary, bold weights
- Monospace: 'Roboto Mono' for case numbers, CPF/CNPJ

**Scale:**
- Page Titles: text-3xl font-bold
- Section Headers: text-2xl font-semibold
- Card Titles: text-xl font-medium
- Body Text: text-base
- Labels/Metadata: text-sm
- Table Headers: text-sm font-semibold uppercase tracking-wide

---

## Layout System

**Spacing Primitives:** Use Tailwind units of 2, 4, 6, 8, 12, 16
- Component padding: p-6
- Section margins: mb-8
- Card spacing: gap-6
- Form field spacing: space-y-4
- Table cell padding: px-6 py-4

**Container Strategy:**
- Dashboard: max-w-7xl mx-auto px-6
- Form pages: max-w-3xl mx-auto px-6
- List/table pages: max-w-full px-6
- Detail views: max-w-5xl mx-auto px-6

---

## Component Library

### Navigation
**Top Navbar:**
- Fixed top position with brand/logo left
- Horizontal module links center
- User menu/logout right
- Dropdown for nested items (Cliente → Casos, Tarefas, etc.)
- Active state indicator with subtle border-bottom

### Dashboard Cards
**Summary Cards Grid:**
- 4-column grid on desktop (grid-cols-1 md:grid-cols-2 lg:grid-cols-4)
- Each card: rounded-lg border with subtle shadow
- Icon top-left, metric number large center, label below
- Status indicators with colored dots
- Clickable cards with hover elevation

### Data Tables
**Table Structure:**
- Full-width responsive tables with horizontal scroll on mobile
- Alternating row backgrounds (stripe pattern)
- Sticky headers on scroll
- Action buttons right-aligned in rows
- Sortable column headers with arrow indicators
- Pagination controls bottom-center
- Search/filter bar above table

### Forms
**Form Layout:**
- Stacked label-above-input pattern
- Input groups for related fields (side-by-side on desktop)
- Required field indicators (asterisk)
- Inline validation with error messages below fields
- Form actions (Submit/Cancel) bottom-right
- Section dividers for multi-section forms

### Detail Views
**Information Cards:**
- Primary info card at top (client/case details)
- Tabbed interface for related data (Processos, Tarefas, Financeiro)
- Action buttons top-right (Edit, Delete, Add Related)
- Metadata footer with created/updated timestamps

### Status Badges
- Pill-shaped badges with appropriate semantic colors
- Task status: To Do, In Progress, Completed
- Case status: Active, Archived, Suspended
- Priority levels: Low, Medium, High
- Transaction types: Income, Expense

### Modals/Dialogs
- Centered overlay with backdrop blur
- Confirmation dialogs for delete actions
- Quick-add forms in modals for rapid data entry

---

## Page-Specific Layouts

### Dashboard
- Welcome header with user name
- 4-card metrics row (Total Clients, Active Cases, Pending Tasks, Month Revenue)
- Two-column layout: Upcoming Events (left) + Recent Tasks (right)
- Quick actions floating action button bottom-right

### List Pages (Clients, Cases, Tasks)
- Page header with title + "Add New" button right
- Filter/search bar with dropdowns for advanced filters
- Data table with pagination
- Empty states with helpful call-to-action

### Detail Pages
- Breadcrumb navigation top
- Header section with entity name and action buttons
- Info card with all core details in grid layout
- Related data in card sections or tabs below
- Timeline/activity log at bottom for case details

### Forms
- Clear page title indicating Create/Edit mode
- Progress indicator for multi-step forms
- Field grouping with subtle section backgrounds
- Helpful placeholder text and validation messages
- Cancel button with confirmation if data entered

### Financial Module
- Period selector (date range) at top
- Summary cards showing Total Income, Expenses, Balance
- Transaction table with filter by type/category
- Visual indicator (red/green) for transaction type

---

## Animations
Use sparingly:
- Smooth transitions on hover states (150ms)
- Page transitions fade (200ms)
- Modal/dropdown entrance (250ms ease-out)
- No scroll-triggered animations

---

## Images
**No hero images** - This is an internal management tool.

**Functional Images:**
- User avatars in top-right menu (circular, 32px)
- Empty state illustrations for lists with no data
- Document/attachment icons in case details
- Brand logo in navbar (max 40px height)

---

## Accessibility
- Proper semantic HTML throughout
- ARIA labels for icon-only buttons
- Focus visible states on all interactive elements
- High contrast text (4.5:1 minimum ratio)
- Keyboard navigation support for all actions
- Form labels properly associated with inputs