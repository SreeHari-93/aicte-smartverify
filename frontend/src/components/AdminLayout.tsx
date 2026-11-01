import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { AdminSidebar } from './AdminSidebar';

export const AdminLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col font-sans overflow-hidden relative">
      {/* 1. Single fixed full-page building background layer with light overlay */}
      <div
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(var(--bg-overlay, rgba(255, 255, 255, 0.12)), var(--bg-overlay, rgba(255, 255, 255, 0.12))), url('/aicte-building.jpeg')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* 2. Fixed Orange Top Bar (Height ~96px) */}
      <TopBar
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      {/* 3. Middle Row: Sidebar + Main Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative z-10">
        {/* Left Admin Sidebar (~255px wide, Cream #FDF0DC) */}
        <AdminSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        {/* Main Content Area: only vertical scrollbar, content scrolls above fixed background */}
        <main className="flex-1 min-w-0 h-full p-4 sm:p-6 lg:p-6 relative overflow-y-auto">
          {/* Page Content Outlet */}
          <div className="max-w-7xl mx-auto w-full flex flex-col min-h-full">
            <div className="flex-1">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
