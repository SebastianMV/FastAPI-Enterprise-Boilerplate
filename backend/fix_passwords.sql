-- Fix password hashes for demo users
UPDATE users SET password_hash = '$2b$12$JQmnR46GHNQFiCdexWCV0OaKvx6DPS5yx/MeFTqQLf71rmLGyo/v6' WHERE email = 'user@example.com';
UPDATE users SET password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYH0q9awqMHO' WHERE email = 'admin@example.com';
UPDATE users SET password_hash = '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi' WHERE email = 'manager@example.com';
