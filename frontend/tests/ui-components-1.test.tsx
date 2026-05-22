import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import {
  Table, TableHeader, TableBody, TableHead, TableRow, TableCell, TableCaption,
} from '@/components/ui/table';

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>Disponible</Badge>);
    expect(screen.getByText('Disponible')).toBeInTheDocument();
  });

  it('applies default variant', () => {
    render(<Badge data-testid="badge">Default</Badge>);
    expect(screen.getByTestId('badge').className).toContain('bg-primary');
  });

  it('applies secondary variant', () => {
    render(<Badge variant="secondary" data-testid="badge">Secondary</Badge>);
    expect(screen.getByTestId('badge').className).toContain('bg-secondary');
  });

  it('applies destructive variant', () => {
    render(<Badge variant="destructive" data-testid="badge">Destructive</Badge>);
    expect(screen.getByTestId('badge').className).toContain('bg-destructive');
  });

  it('applies outline variant', () => {
    render(<Badge variant="outline" data-testid="badge">Outline</Badge>);
    expect(screen.getByTestId('badge').className).toContain('text-foreground');
  });
});

// ---------------------------------------------------------------------------
// Button
// ---------------------------------------------------------------------------

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('calls onClick', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('is disabled when disabled prop is set', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('does not call onClick when disabled', async () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Disabled</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('applies variant classes', () => {
    render(<Button variant="destructive" data-testid="btn">Delete</Button>);
    expect(screen.getByTestId('btn').className).toContain('bg-destructive');
  });

  it('applies size classes', () => {
    render(<Button size="lg" data-testid="btn">Large</Button>);
    expect(screen.getByTestId('btn').className).toContain('h-11');
  });
});

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

describe('Card', () => {
  it('renders Card with header, title, description, content, footer', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
        </CardHeader>
        <CardContent>Content</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
    expect(screen.getByText('Footer')).toBeInTheDocument();
  });

  it('renders CardTitle as h3', () => {
    render(<CardTitle>Heading</CardTitle>);
    expect(screen.getByText('Heading').tagName).toBe('H3');
  });
});

// ---------------------------------------------------------------------------
// Alert
// ---------------------------------------------------------------------------

describe('Alert', () => {
  it('renders with title and description', () => {
    render(
      <Alert>
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Something went wrong</AlertDescription>
      </Alert>
    );
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('has role alert', () => {
    render(<Alert data-testid="alert">Alert</Alert>);
    expect(screen.getByTestId('alert')).toHaveAttribute('role', 'alert');
  });

  it('applies destructive variant', () => {
    render(<Alert variant="destructive" data-testid="alert">Error</Alert>);
    expect(screen.getByTestId('alert').className).toContain('border-destructive');
  });
});

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

describe('Table', () => {
  it('renders headers and rows', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Unit 1</TableCell>
            <TableCell>Available</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Unit 1')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
  });

  it('renders caption', () => {
    render(
      <Table>
        <TableCaption>Units list</TableCaption>
        <TableBody><TableRow><TableCell>Data</TableCell></TableRow></TableBody>
      </Table>
    );
    expect(screen.getByText('Units list')).toBeInTheDocument();
  });
});
