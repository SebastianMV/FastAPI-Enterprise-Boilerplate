/**
 * Unit tests for Modal component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal, ConfirmModal } from './Modal';

describe('Modal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    title: 'Test Modal',
    children: <p>Modal content</p>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe('Basic rendering', () => {
    it('should render when isOpen is true', () => {
      render(<Modal {...defaultProps} />);
      
      expect(screen.getByText('Test Modal')).toBeInTheDocument();
      expect(screen.getByText('Modal content')).toBeInTheDocument();
    });

    it('should not render when isOpen is false', () => {
      render(<Modal {...defaultProps} isOpen={false} />);
      
      expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
    });

    it('should render title correctly', () => {
      render(<Modal {...defaultProps} title="Custom Title" />);
      
      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Custom Title');
    });

    it('should render children content', () => {
      render(
        <Modal {...defaultProps}>
          <div data-testid="custom-content">Custom content here</div>
        </Modal>
      );
      
      expect(screen.getByTestId('custom-content')).toBeInTheDocument();
    });
  });

  describe('Size variants', () => {
    it.each(['sm', 'md', 'lg', 'xl'] as const)('should render with size %s', (size) => {
      render(<Modal {...defaultProps} size={size} />);
      
      expect(screen.getByText('Test Modal')).toBeInTheDocument();
    });

    it('should default to md size', () => {
      render(<Modal {...defaultProps} />);
      
      // Modal should be present (default size applied internally)
      expect(screen.getByText('Test Modal')).toBeInTheDocument();
    });
  });

  describe('Close behavior', () => {
    it('should call onClose when close button is clicked', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      
      render(<Modal {...defaultProps} onClose={onClose} />);
      
      const closeButton = screen.getByRole('button');
      await user.click(closeButton);
      
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when clicking backdrop', async () => {
      const onClose = vi.fn();
      
      render(<Modal {...defaultProps} onClose={onClose} />);
      
      // Click the backdrop (the div with backdrop blur)
      const backdrop = document.querySelector('.bg-black\\/50');
      if (backdrop) {
        fireEvent.click(backdrop);
      }
      
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('should call onClose when Escape key is pressed', () => {
      const onClose = vi.fn();
      
      render(<Modal {...defaultProps} onClose={onClose} />);
      
      fireEvent.keyDown(document, { key: 'Escape' });
      
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Body overflow management', () => {
    it('should set body overflow to hidden when open', () => {
      render(<Modal {...defaultProps} isOpen={true} />);
      
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('should restore body overflow when closed', () => {
      const { rerender } = render(<Modal {...defaultProps} isOpen={true} />);
      
      rerender(<Modal {...defaultProps} isOpen={false} />);
      
      expect(document.body.style.overflow).toBe('unset');
    });
  });

  describe('Accessibility', () => {
    it('should have close button', () => {
      render(<Modal {...defaultProps} />);
      
      const closeButton = screen.getByRole('button');
      expect(closeButton).toBeInTheDocument();
    });

    it('should be focusable', () => {
      render(<Modal {...defaultProps} />);
      
      // The modal container should have tabIndex
      const modalContainer = document.querySelector('[tabindex="-1"]');
      expect(modalContainer).toBeInTheDocument();
    });
  });
});

describe('ConfirmModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('should render title and message', () => {
    render(<ConfirmModal {...defaultProps} />);
    
    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
  });

  it('should render default button texts', () => {
    render(<ConfirmModal {...defaultProps} />);
    
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
  });

  it('should render custom button texts', () => {
    render(
      <ConfirmModal 
        {...defaultProps} 
        confirmText="Delete" 
        cancelText="Go Back" 
      />
    );
    
    expect(screen.getByRole('button', { name: 'Go Back' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('should call onConfirm when confirm button is clicked', async () => {
    const onConfirm = vi.fn();
    const user = userEvent.setup();
    
    render(<ConfirmModal {...defaultProps} onConfirm={onConfirm} />);
    
    await user.click(screen.getByRole('button', { name: /confirm/i }));
    
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('should call onClose when cancel button is clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    
    render(<ConfirmModal {...defaultProps} onClose={onClose} />);
    
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should show loading state', () => {
    render(<ConfirmModal {...defaultProps} isLoading={true} />);
    
    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    expect(confirmButton).toBeDisabled();
  });

  describe('Variants', () => {
    it.each(['danger', 'warning', 'info'] as const)('should render %s variant', (variant) => {
      render(<ConfirmModal {...defaultProps} variant={variant} />);
      
      expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    });
  });
});
