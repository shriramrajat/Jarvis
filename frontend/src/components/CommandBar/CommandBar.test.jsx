import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CommandBar from './CommandBar';

describe('CommandBar Component', () => {
  it('disables input when disconnected', () => {
    render(<CommandBar onSend={() => {}} jarvisState="IDLE" connected={false} />);
    const input = screen.getByRole('textbox');
    
    expect(input).toBeDisabled();
    expect(input).toHaveAttribute('placeholder', 'Offline...');
  });

  it('enables input when connected', () => {
    render(<CommandBar onSend={() => {}} jarvisState="IDLE" connected={true} />);
    const input = screen.getByRole('textbox');
    
    expect(input).not.toBeDisabled();
    expect(input).toHaveAttribute('placeholder', 'Awaiting input...');
  });

  it('triggers onSend callback with typed text on Enter key press', () => {
    const onSendMock = vi.fn();
    render(<CommandBar onSend={onSendMock} jarvisState="IDLE" connected={true} />);
    
    const input = screen.getByRole('textbox');
    
    // Type in input
    fireEvent.change(input, { target: { value: 'tell me a joke' } });
    expect(input.value).toBe('tell me a joke');
    
    // Press Enter
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', charCode: 13 });
    
    expect(onSendMock).toHaveBeenCalledWith('tell me a joke');
    // Input should be cleared after enter
    expect(input.value).toBe('');
  });

  it('does not trigger onSend callback if input is empty or contains only spaces', () => {
    const onSendMock = vi.fn();
    render(<CommandBar onSend={onSendMock} jarvisState="IDLE" connected={true} />);
    
    const input = screen.getByRole('textbox');
    
    // Empty input Enter
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSendMock).not.toHaveBeenCalled();
    
    // Space only input Enter
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(onSendMock).not.toHaveBeenCalled();
  });
});
