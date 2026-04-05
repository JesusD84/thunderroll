
'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LogIn, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { signIn, useSession } from 'next-auth/react';

export default function LoginPage() {
  const router = useRouter();
  const { data: session, status } = useSession() || {};
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Redirigir si ya está autenticado
  useEffect(() => {
    if (status === 'authenticated' && session) {
      router.push('/');
    }
  }, [status, session, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const result = await signIn('credentials', {
        email: credentials.email,
        password: credentials.password,
        redirect: false,
      });

      if (result?.error) {
        setError('Credenciales inválidas. Verifica el email y contraseña.');
      } else if (result?.ok) {
        router.push('/');
      }
    } catch (error) {
      setError('Error de conexión. Intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-blue-600 mb-2">Thunderrol</h1>
          <h2 className="text-2xl font-bold text-gray-900">Iniciar Sesión</h2>
          <p className="mt-2 text-sm text-gray-600">
            Sistema de Trazabilidad de Inventario
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <Card>
          <CardHeader>
            <CardTitle className="text-center">Acceso al Sistema</CardTitle>
            <CardDescription className="text-center">
              Ingresa tus credenciales para continuar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={credentials.email}
                  onChange={(e) => setCredentials(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="usuario@thunderrol.com"
                  required
                />
              </div>

              <div>
                <Label htmlFor="password">Contraseña</Label>
                <Input
                  id="password"
                  type="password"
                  value={credentials.password}
                  onChange={(e) => setCredentials(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="••••••••"
                  required
                />
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  'Iniciando Sesión...'
                ) : (
                  <>
                    <LogIn className="mr-2 h-4 w-4" />
                    Iniciar Sesión
                  </>
                )}
              </Button>
            </form>

            {/* Credenciales Demo */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Credenciales Demo:</h3>
              <div className="space-y-2 text-xs text-gray-600">
                <div><strong>Admin:</strong> admin@thunderrol.com / admin123</div>
                <div><strong>Manager:</strong> manager@thunderrol.com / manager123</div>
                <div><strong>Inventario:</strong> inventario@thunderrol.com / inventario123</div>
                <div><strong>Taller:</strong> taller@thunderrol.com / taller123</div>
                <div><strong>Ventas:</strong> ventas@thunderrol.com / ventas123</div>
                <div><strong>Consultor:</strong> consultas@thunderrol.com / consultas123</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
