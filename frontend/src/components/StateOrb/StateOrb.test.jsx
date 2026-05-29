import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StateOrb from './StateOrb';

describe('StateOrb Component', () => {
  it('renders with default IDLE state and NORMAL mode', () => {
    const { container } = render(<StateOrb state="IDLE" mode="NORMAL" />);
    
    // Asserts that the state and mode text are rendered
    expect(screen.getByText('IDLE')).toBeInTheDocument();
    expect(screen.getByText('NORMAL MODE')).toBeInTheDocument();
    
    // Asserts that the CSS class contains the lowercased state name
    const reactor = container.querySelector('.arc-reactor');
    expect(reactor).toHaveClass('arc-reactor--idle');
  });

  it('renders correctly with SPEAKING state and FOCUS mode', () => {
    const { container } = render(<StateOrb state="SPEAKING" mode="FOCUS" />);
    
    expect(screen.getByText('SPEAKING')).toBeInTheDocument();
    expect(screen.getByText('FOCUS MODE')).toBeInTheDocument();
    
    const reactor = container.querySelector('.arc-reactor');
    expect(reactor).toHaveClass('arc-reactor--speaking');
  });

  it('shows pulse animation element for listening and speaking states', () => {
    const { container, rerender } = render(<StateOrb state="LISTENING" mode="NORMAL" />);
    
    // LISTENING has pulse element
    expect(container.querySelector('.arc-pulse')).toBeInTheDocument();
    
    // THINKING does not have pulse element
    rerender(<StateOrb state="THINKING" mode="NORMAL" />);
    expect(container.querySelector('.arc-pulse')).not.toBeInTheDocument();
  });
});
