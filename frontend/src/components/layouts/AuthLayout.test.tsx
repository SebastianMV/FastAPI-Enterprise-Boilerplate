/**
 * Unit tests for AuthLayout component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AuthLayout from './AuthLayout';

describe('AuthLayout', () => {
  it('should render outlet content', () => {
    render(
      <MemoryRouter initialEntries={['/test']}>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/test" element={<div>Test Child</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Test Child')).toBeInTheDocument();
  });

  it('should render with proper styling classes', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/test']}>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/test" element={<div>Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
    const wrapper = container.firstElementChild;
    expect(wrapper?.classList.contains('min-h-screen')).toBe(true);
  });
});
