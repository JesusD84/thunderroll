
import { NextRequest, NextResponse } from 'next/server';
import { PrismaClient, UserRole, UserStatus } from '@prisma/client';
import bcrypt from 'bcryptjs';

export const dynamic = "force-dynamic";

const prisma = new PrismaClient();

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, password, name, role } = body;

    // Validar datos requeridos
    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email y contraseña son requeridos' },
        { status: 400 }
      );
    }

    // Validar y mapear rol
    let userRole: UserRole = UserRole.VIEWER; // Rol por defecto
    
    if (role) {
      const roleMap: { [key: string]: UserRole } = {
        'ADMIN': UserRole.ADMIN,
        'MANAGER': UserRole.MANAGER,
        'OPERATOR': UserRole.OPERATOR,
        'VIEWER': UserRole.VIEWER,
        // Mapeos adicionales para casos comunes
        'admin': UserRole.ADMIN,
        'manager': UserRole.MANAGER,
        'operator': UserRole.OPERATOR,
        'viewer': UserRole.VIEWER,
        'user': UserRole.VIEWER,
      };
      
      userRole = roleMap[role] || UserRole.VIEWER;
    }

    // Verificar si el usuario ya existe
    const existingUser = await prisma.user.findUnique({
      where: { email }
    });

    if (existingUser) {
      return NextResponse.json(
        { error: 'El usuario ya existe' },
        { status: 409 }
      );
    }

    // Hashear contraseña
    const hashedPassword = await bcrypt.hash(password, 10);

    // Crear usuario
    const user = await prisma.user.create({
      data: {
        email,
        hashedPassword,
        name: name || email,
        role: userRole,
        status: UserStatus.ACTIVE,
      },
      select: {
        id: true,
        email: true,
        name: true,
        role: true,
        createdAt: true,
      }
    });

    return NextResponse.json(
      { 
        message: 'Usuario creado exitosamente',
        user: {
          id: user.id,
          email: user.email,
          name: user.name,
          role: user.role
        }
      },
      { status: 201 }
    );

  } catch (error) {
    console.error('Error creating user:', error);
    return NextResponse.json(
      { error: 'Error interno del servidor' },
      { status: 500 }
    );
  }
}
