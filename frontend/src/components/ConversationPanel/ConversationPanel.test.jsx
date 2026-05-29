import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ConversationPanel from './ConversationPanel';

describe('ConversationPanel Component', () => {
  it('renders empty message when there are no messages', () => {
    render(<ConversationPanel messages={[]} respondToPermission={() => {}} />);
    expect(screen.getByText('No recent interactions.')).toBeInTheDocument();
  });

  it('renders messages with role and content', () => {
    const mockMessages = [
      { id: '1', role: 'user', content: 'hello JARVIS', timestamp: new Date().toISOString() },
      { id: '2', role: 'jarvis', content: 'Hello, sir.', timestamp: new Date().toISOString() }
    ];

    render(<ConversationPanel messages={mockMessages} respondToPermission={() => {}} />);
    
    expect(screen.getByText('USER')).toBeInTheDocument();
    expect(screen.getByText('hello JARVIS')).toBeInTheDocument();
    
    expect(screen.getByText('JARVIS')).toBeInTheDocument();
    expect(screen.getByText('Hello, sir.')).toBeInTheDocument();
  });

  it('renders unresolved permission requests with ALLOW and DENY buttons', () => {
    const mockMessages = [
      {
        id: '1',
        role: 'jarvis',
        content: 'I need your permission to run a command.',
        isPermissionRequest: true,
        command_id: 'cmd_123',
        action: 'RUN_COMMAND',
        params: { command: 'echo "hello"' }
      }
    ];

    const respondMock = vi.fn();

    render(<ConversationPanel messages={mockMessages} respondToPermission={respondMock} />);
    
    expect(screen.getByText('ALLOW')).toBeInTheDocument();
    expect(screen.getByText('DENY')).toBeInTheDocument();
    expect(screen.getByText('ACTION:')).toBeInTheDocument();
    expect(screen.getByText('RUN_COMMAND')).toBeInTheDocument();

    // Trigger button clicks
    fireEvent.click(screen.getByText('ALLOW'));
    expect(respondMock).toHaveBeenCalledWith('cmd_123', true);

    fireEvent.click(screen.getByText('DENY'));
    expect(respondMock).toHaveBeenCalledWith('cmd_123', false);
  });

  it('renders resolved permission status instead of buttons', () => {
    const mockMessages = [
      {
        id: '1',
        role: 'jarvis',
        content: 'I need your permission to run a command.',
        isPermissionRequest: true,
        command_id: 'cmd_123',
        action: 'RUN_COMMAND',
        params: { command: 'echo "hello"' },
        permissionResolved: 'allowed'
      }
    ];

    render(<ConversationPanel messages={mockMessages} respondToPermission={() => {}} />);
    
    expect(screen.queryByText('ALLOW')).not.toBeInTheDocument();
    expect(screen.queryByText('DENY')).not.toBeInTheDocument();
    expect(screen.getByText('● ACTION ALLOWED')).toBeInTheDocument();
  });
});
