import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

function Hello({ name }: { name: string }) {
  return <h1>Hello, {name}!</h1>;
}

describe('Infra smoke test', () => {
  it('renders a component', () => {
    render(<Hello name="Thunderrol" />);
    expect(screen.getByText('Hello, Thunderrol!')).toBeInTheDocument();
  });
});
