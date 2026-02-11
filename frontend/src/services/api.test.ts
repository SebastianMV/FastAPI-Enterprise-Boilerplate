/**
 * Tests for API service layer.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';

// Mock axios before imports
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    put: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
  };
});

// Import after mock
import { authService, usersService } from './api';

describe('API Services', () => {
  let mockApi: {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Get the mocked axios instance
    mockApi = (axios.create as ReturnType<typeof vi.fn>)();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('authService', () => {
    describe('login', () => {
      it('should call /auth/login with credentials', async () => {
        const mockResponse = {
          data: {
            access_token: 'test-token',
            refresh_token: 'refresh-token',
            token_type: 'bearer',
            expires_in: 3600,
            user: { id: '1', email: 'test@example.com' },
          },
        };
        mockApi.post.mockResolvedValueOnce(mockResponse);

        const credentials = { email: 'test@example.com', password: 'password123' };
        const result = await authService.login(credentials);

        expect(mockApi.post).toHaveBeenCalledWith('/auth/login', credentials);
        expect(result).toEqual(mockResponse.data);
      });

      it('should handle login with MFA code', async () => {
        const mockResponse = {
          data: {
            access_token: 'test-token',
            refresh_token: 'refresh-token',
            token_type: 'bearer',
            expires_in: 3600,
            user: { id: '1', email: 'test@example.com' },
          },
        };
        mockApi.post.mockResolvedValueOnce(mockResponse);

        const credentials = { 
          email: 'test@example.com', 
          password: 'password123',
          mfa_code: '123456'
        };
        await authService.login(credentials);

        expect(mockApi.post).toHaveBeenCalledWith('/auth/login', credentials);
      });

      it('should throw on login failure', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Invalid credentials'));

        await expect(
          authService.login({ email: 'test@example.com', password: 'wrong' })
        ).rejects.toThrow('Invalid credentials');
      });
    });

    describe('logout', () => {
      it('should call /auth/logout', async () => {
        mockApi.post.mockResolvedValueOnce({ data: {} });

        await authService.logout();

        expect(mockApi.post).toHaveBeenCalledWith('/auth/logout');
      });
    });

    describe('refresh', () => {
      it('should call /auth/refresh with empty body', async () => {
        const mockResponse = {
          data: {
            access_token: 'new-token',
            token_type: 'bearer',
            expires_in: 3600,
          },
        };
        mockApi.post.mockResolvedValueOnce(mockResponse);

        const result = await authService.refresh();

        expect(mockApi.post).toHaveBeenCalledWith('/auth/refresh', {});
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('me', () => {
      it('should call /auth/me and return user', async () => {
        const mockUser = {
          id: '1',
          email: 'test@example.com',
          first_name: 'Test',
          last_name: 'User',
          is_active: true,
          is_superuser: false,
          email_verified: true,
          created_at: '2024-01-01T00:00:00Z',
        };
        mockApi.get.mockResolvedValueOnce({ data: mockUser });

        const result = await authService.me();

        expect(mockApi.get).toHaveBeenCalledWith('/auth/me');
        expect(result).toEqual(mockUser);
      });
    });
  });

  describe('usersService', () => {
    describe('list', () => {
      it('should call /users with default params', async () => {
        const mockResponse = {
          data: {
            items: [{ id: '1', email: 'user@example.com' }],
            total: 1,
            skip: 0,
            limit: 10,
          },
        };
        mockApi.get.mockResolvedValueOnce(mockResponse);

        const result = await usersService.list();

        expect(mockApi.get).toHaveBeenCalledWith('/users', { params: undefined });
        expect(result).toEqual(mockResponse.data);
      });

      it('should call /users with pagination params', async () => {
        const mockResponse = {
          data: {
            items: [],
            total: 100,
            skip: 20,
            limit: 10,
          },
        };
        mockApi.get.mockResolvedValueOnce(mockResponse);

        await usersService.list({ skip: 20, limit: 10 });

        expect(mockApi.get).toHaveBeenCalledWith('/users', { 
          params: { skip: 20, limit: 10 } 
        });
      });
    });

    describe('get', () => {
      it('should call /users/:id', async () => {
        const mockUser = { id: '123', email: 'user@example.com' };
        mockApi.get.mockResolvedValueOnce({ data: mockUser });

        const result = await usersService.get('123');

        expect(mockApi.get).toHaveBeenCalledWith('/users/123');
        expect(result).toEqual(mockUser);
      });
    });

    describe('create', () => {
      it('should call POST /users with data', async () => {
        const userData = {
          email: 'new@example.com',
          password: 'password123',
          first_name: 'New',
          last_name: 'User',
        };
        const mockResponse = { data: { id: '1', ...userData } };
        mockApi.post.mockResolvedValueOnce(mockResponse);

        const result = await usersService.create(userData);

        expect(mockApi.post).toHaveBeenCalledWith('/users', userData);
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('update', () => {
      it('should call PATCH /users/:id with data', async () => {
        const updateData = { first_name: 'Updated' };
        const mockResponse = { data: { id: '123', ...updateData } };
        mockApi.patch.mockResolvedValueOnce(mockResponse);

        const result = await usersService.update('123', updateData);

        expect(mockApi.patch).toHaveBeenCalledWith('/users/123', updateData);
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('updateMe', () => {
      it('should call PATCH /users/me with data', async () => {
        const updateData = { first_name: 'Updated', last_name: 'Name' };
        const mockResponse = { data: { id: '1', ...updateData } };
        mockApi.patch.mockResolvedValueOnce(mockResponse);

        const result = await usersService.updateMe(updateData);

        expect(mockApi.patch).toHaveBeenCalledWith('/users/me', updateData);
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('uploadAvatar', () => {
      it('should call POST /users/me/avatar with FormData', async () => {
        const mockFile = new File(['test'], 'avatar.png', { type: 'image/png' });
        const mockResponse = { data: { id: '1', avatar_url: '/avatars/test.png' } };
        mockApi.post.mockResolvedValueOnce(mockResponse);

        const result = await usersService.uploadAvatar(mockFile);

        expect(mockApi.post).toHaveBeenCalledWith(
          '/users/me/avatar',
          expect.any(FormData),
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
        expect(result).toEqual(mockResponse.data);
      });
    });
  });
});

describe('API Interceptors', () => {
  it('should have axios module available', () => {
    // Verify axios module is available for mocking
    expect(axios.create).toBeDefined();
    expect(typeof axios.create).toBe('function');
  });
});