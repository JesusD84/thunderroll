
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { useSession, signOut } from 'next-auth/react';
import { 
  Home, 
  Package, 
  Upload, 
  Truck, 
  FileText, 
  Settings, 
  LogOut,
  Menu,
  X
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Unidades', href: '/units', icon: Package },
  { name: 'Importar', href: '/imports', icon: Upload },
  { name: 'Transferencias', href: '/transfers', icon: Truck },
  { name: 'Reportes', href: '/reports', icon: FileText },
  { name: 'Configuración', href: '/settings', icon: Settings },
];

export default function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession() || {};

  // Redirigir a login si no está autenticado
  useEffect(() => {
    if (status === 'unauthenticated' && pathname !== '/login') {
      router.push('/login');
    }
  }, [status, pathname, router]);

  const handleLogout = async () => {
    await signOut({ redirect: false });
    router.push('/login');
  };

  // No mostrar navegación en la página de login o mientras está cargando
  if (pathname === '/login' || status === 'loading') {
    return null;
  }

  // No mostrar navegación si no está autenticado
  if (status === 'unauthenticated') {
    return null;
  }

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 bg-white shadow-sm z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link href="/" className="text-xl font-bold text-blue-600">
                  Thunderrol
                </Link>
              </div>
              
              {/* Desktop Navigation */}
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {navigation.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`}
                    >
                      <Icon className="mr-2 h-4 w-4" />
                      {item.name}
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* User Menu */}
            <div className="hidden sm:ml-6 sm:flex sm:items-center">
              <div className="flex items-center space-x-4">
                <div className="text-sm">
                  <div className="text-gray-900">{session?.user?.name}</div>
                  <div className="text-gray-500 text-xs">{(session?.user as any)?.role}</div>
                </div>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Salir
                </Button>
              </div>
            </div>

            {/* Mobile menu button */}
            <div className="sm:hidden flex items-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <Menu className="h-6 w-6" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="sm:hidden">
            <div className="pt-2 pb-3 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
                      isActive
                        ? 'bg-blue-50 border-blue-500 text-blue-700'
                        : 'border-transparent text-gray-600 hover:bg-gray-50 hover:border-gray-300 hover:text-gray-800'
                    }`}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <Icon className="inline mr-2 h-5 w-5" />
                    {item.name}
                  </Link>
                );
              })}
              
              <div className="border-t border-gray-200 pt-4 pb-3">
                <div className="px-3 py-2">
                  <div className="text-sm text-gray-900 font-medium">{session?.user?.name}</div>
                  <div className="text-sm text-gray-500 mb-3">{(session?.user as any)?.role}</div>
                  <Button variant="ghost" size="sm" onClick={handleLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    Salir
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </nav>
    </>
  );
}
