import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../../App';

vi.mock('../../features/dashboard', () => ({
  Dashboard: () => <div />,
}));

describe('App login route', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/login');
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('renders the sign-in button at /login', () => {
    render(<App />);

    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
  });
});
