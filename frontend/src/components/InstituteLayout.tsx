import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';

export const InstituteLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col font-sans bg-slate-100">
      {/* 1. Fixed Orange Top Bar (Height ~96px) */}
      <TopBar
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      {/* 2. Middle Row: Sidebar + Main Area */}
      <div className="flex-1 flex min-h-[calc(100vh-96px)] relative">
        {/* Left Sidebar (~255px wide, Cream #FDF0DC) */}
        <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        {/* Main Content Area with full-bleed institute.jpg background */}
        <main
          className="flex-1 min-w-0 p-4 sm:p-6 md:p-8 lg:p-10 relative overflow-y-auto"
          style={{
            backgroundImage: "url('/institute.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            backgroundAttachment: 'fixed',
          }}
        >
          {/* Subtle light overlay to ensure text contrast over building background */}
          <div className="absolute inset-0 bg-black/15 pointer-events-none z-0" />

          {/* Page Content Outlet (relative z-10 for cards to float over image) */}
          <div className="relative z-10 max-w-7xl mx-auto w-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

