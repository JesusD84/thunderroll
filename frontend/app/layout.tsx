
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Navigation from '@/components/Navigation';
import SessionProvider from '@/components/providers/SessionProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Thunderrol - Sistema de Trazabilidad',
  description: 'Sistema de trazabilidad de inventario para Thunderrol',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className={inter.className}>
        <SessionProvider>
          <Navigation />
          <div className="pt-16">
            {children}
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}
