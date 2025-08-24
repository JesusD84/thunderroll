
import { PrismaClient, UserRole, UserStatus } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Iniciando seed de la base de datos...');

  // Limpiar datos existentes si es necesario
  console.log('🗑️  Limpiando datos existentes...');
  await prisma.verificationToken.deleteMany();
  await prisma.session.deleteMany();
  await prisma.account.deleteMany();
  await prisma.user.deleteMany();

  // Crear usuarios demo
  console.log('👤 Creando usuarios demo...');

  const users = [
    // Usuario de prueba requerido para testing
    {
      email: 'john@doe.com',
      password: 'johndoe123',
      name: 'John Doe',
      role: UserRole.ADMIN,
      department: 'Testing',
      phone: '+52 33 0000-0000'
    },
    {
      email: 'admin@thunderrol.com',
      password: 'admin123',
      name: 'Administrator',
      role: UserRole.ADMIN,
      department: 'IT',
      phone: '+52 33 1234-5678'
    },
    {
      email: 'manager@thunderrol.com', 
      password: 'manager123',
      name: 'Gerente de Inventario',
      role: UserRole.MANAGER,
      department: 'Inventario',
      phone: '+52 33 1234-5679'
    },
    {
      email: 'inventario@thunderrol.com',
      password: 'inventario123', 
      name: 'Operador de Inventario',
      role: UserRole.OPERATOR,
      department: 'Inventario',
      phone: '+52 33 1234-5680'
    },
    {
      email: 'taller@thunderrol.com',
      password: 'taller123',
      name: 'Técnico de Taller',
      role: UserRole.OPERATOR,
      department: 'Taller',
      phone: '+52 33 1234-5681'
    },
    {
      email: 'ventas@thunderrol.com',
      password: 'ventas123',
      name: 'Vendedor',
      role: UserRole.OPERATOR,
      department: 'Ventas',
      phone: '+52 33 1234-5682'
    },
    {
      email: 'consultas@thunderrol.com',
      password: 'consultas123',
      name: 'Consultor',
      role: UserRole.VIEWER,
      department: 'Consultas',
      phone: '+52 33 1234-5683'
    }
  ];

  let adminUser: { id: string } | null = null;

  for (const userData of users) {
    console.log(`   📝 Creando usuario: ${userData.email}`);
    
    // Hashear contraseña
    const hashedPassword = await bcrypt.hash(userData.password, 10);
    
    const user: { id: string; role: UserRole; email: string } = await prisma.user.create({
      data: {
        email: userData.email,
        hashedPassword: hashedPassword,
        name: userData.name,
        role: userData.role,
        status: UserStatus.ACTIVE,
        department: userData.department,
        phone: userData.phone,
        createdBy: adminUser?.id || null,
      },
      select: {
        id: true,
        role: true,
        email: true
      }
    });

    // Guardar referencia al admin para los usuarios siguientes
    if (userData.role === UserRole.ADMIN && !adminUser) {
      adminUser = user;
    }

    console.log(`   ✅ Usuario creado: ${user.email} (${user.role})`);
  }

  console.log('🎉 Seed completado exitosamente!');
  console.log('');
  console.log('📋 Usuarios creados:');
  console.log('┌─────────────────────────────────┬─────────────┬───────────┐');
  console.log('│ Email                           │ Contraseña  │ Rol       │');
  console.log('├─────────────────────────────────┼─────────────┼───────────┤');
  
  for (const user of users) {
    const roleLabel = user.role === UserRole.ADMIN ? 'ADMIN    ' :
                      user.role === UserRole.MANAGER ? 'MANAGER  ' :
                      user.role === UserRole.OPERATOR ? 'OPERATOR ' :
                      'VIEWER   ';
    console.log(`│ ${user.email.padEnd(31)} │ ${user.password.padEnd(11)} │ ${roleLabel} │`);
  }
  console.log('└─────────────────────────────────┴─────────────┴───────────┘');
  console.log('');
  console.log('🚀 Puedes usar cualquier combinación de email/contraseña para hacer login.');
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (e) => {
    console.error('Error durante el seed:', e);
    await prisma.$disconnect();
    process.exit(1);
  });
