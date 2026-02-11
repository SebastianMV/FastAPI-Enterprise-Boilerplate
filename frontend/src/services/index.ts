/**
 * Services barrel file.
 * 
 * Re-exports all domain services and their types for backward compatibility.
 * New code should import directly from the specific service file:
 *   import { authService } from '@/services/authService';
 * 
 * Legacy imports still work:
 *   import { authService } from '@/services/api';
 */

// Core API instance
export { default as api } from './api';

// Domain services
export { authService } from './authService';
export { usersService } from './usersService';
export { dashboardService } from './dashboardService';
export { oauthService, OAUTH_PROVIDERS } from './oauthService';
export { searchService } from './searchService';
export { notificationsService } from './notificationsService';
export { configService } from './configService';
export { sessionsService } from './sessionsService';
export { emailVerificationService } from './emailVerificationService';
export { rolesService } from './rolesService';
export { auditLogsService } from './auditLogsService';
export { tenantsService } from './tenantsService';
export { dataExchangeService } from './dataExchangeService';
export { mfaService } from './mfaService';

// Re-export all types
export type { User, LoginCredentials, LoginResponse, RefreshResponse, PaginatedResponse } from './api';
export type { StatItem, ActivityItem, DashboardStats, RecentActivity, SystemHealth } from './dashboardService';
export type { OAuthProvider, OAuthAuthorizeResponse, OAuthConnection } from './oauthService';
export type { SearchFilter, SearchSort, SearchRequest, SearchHit, SearchResponse, SearchSuggestion } from './searchService';
export type { Notification, NotificationsResponse } from './notificationsService';
export type { FeatureConfig } from './configService';
export type { UserSession, SessionListResponse, RevokeSessionsResponse } from './sessionsService';
export type { VerificationStatus } from './emailVerificationService';
export type { Role, RoleListResponse, CreateRoleData, UpdateRoleData, UserPermissions, AssignRoleRequest } from './rolesService';
export type { AuditLog, AuditLogListResponse, AuditLogFilters } from './auditLogsService';
export type { Tenant, TenantSettings, TenantListResponse, CreateTenantData, UpdateTenantData } from './tenantsService';
export type { EntityField, Entity, ExportPreview, ImportResult, ReportFilter, ReportRequest } from './dataExchangeService';
export type { MFAStatus, MFASetupResponse, EmailOTPResponse } from './mfaService';
