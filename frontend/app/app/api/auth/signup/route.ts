
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    
    // En este sistema no permitimos registro libre
    // Solo existen usuarios predefinidos
    return NextResponse.json(
      { error: 'El registro no está habilitado. Contacta al administrador.' },
      { status: 403 }
    );
  } catch (error) {
    return NextResponse.json(
      { error: 'Error procesando solicitud' },
      { status: 400 }
    );
  }
}
