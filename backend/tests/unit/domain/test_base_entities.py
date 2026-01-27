# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Unit tests for base entities."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from app.domain.entities.base import (
    AuditableEntity,
    BaseEntity,
    SoftDeletableEntity,
    TenantEntity,
)


class TestBaseEntity:
    """Tests for BaseEntity."""
    
    def test_entity_creation(self):
        """Test creating base entity with auto-generated ID."""
        entity = BaseEntity()
        assert entity.id is not None
    
    def test_entity_with_id(self):
        """Test creating entity with specific ID."""
        entity_id = uuid4()
        entity = BaseEntity(id=entity_id)
        assert entity.id == entity_id
    
    def test_entity_equality(self):
        """Test entities are equal by ID."""
        entity_id = uuid4()
        entity1 = BaseEntity(id=entity_id)
        entity2 = BaseEntity(id=entity_id)
        entity3 = BaseEntity()
        
        assert entity1 == entity2
        assert entity1 != entity3
    
    def test_entity_hash(self):
        """Test entities can be used in sets."""
        entity_id = uuid4()
        entity1 = BaseEntity(id=entity_id)
        entity2 = BaseEntity(id=entity_id)
        entity3 = BaseEntity()
        
        entities = {entity1, entity2, entity3}
        assert len(entities) == 2

    def test_entity_equality_with_non_entity(self):
        """Test entity is not equal to non-entity types."""
        entity = BaseEntity()
        
        # Comparing with non-BaseEntity types returns False
        assert (entity == "string") is False
        assert (entity == 123) is False
        assert (entity == None) is False
        assert (entity == {"id": str(entity.id)}) is False
        assert (entity == [entity.id]) is False


class TestAuditableEntity:
    """Tests for AuditableEntity."""
    
    def test_auditable_creation(self):
        """Test auditable entity has timestamps."""
        entity = AuditableEntity()
        
        assert entity.created_at is not None
        assert entity.updated_at is not None
        assert entity.created_by is None
        assert entity.updated_by is None
    
    def test_mark_updated(self):
        """Test marking entity as updated."""
        entity = AuditableEntity()
        original_updated_at = entity.updated_at
        
        user_id = uuid4()
        entity.mark_updated(by_user=user_id)
        
        assert entity.updated_at >= original_updated_at
        assert entity.updated_by == user_id


class TestTenantEntity:
    """Tests for TenantEntity."""
    
    def test_tenant_entity_creation(self):
        """Test tenant entity has tenant_id."""
        entity = TenantEntity()
        assert entity.tenant_id is not None
    
    def test_tenant_entity_with_tenant_id(self):
        """Test creating entity with specific tenant_id."""
        tenant_id = uuid4()
        entity = TenantEntity(tenant_id=tenant_id)
        assert entity.tenant_id == tenant_id


class TestSoftDeletableEntity:
    """Tests for SoftDeletableEntity."""
    
    def test_soft_deletable_creation(self):
        """Test soft deletable entity defaults."""
        entity = SoftDeletableEntity()
        
        assert entity.is_deleted is False
        assert entity.deleted_at is None
        assert entity.deleted_by is None
    
    def test_soft_delete(self):
        """Test soft deleting entity."""
        entity = SoftDeletableEntity()
        user_id = uuid4()
        
        entity.soft_delete(by_user=user_id)
        
        assert entity.is_deleted is True
        assert entity.deleted_at is not None
        assert entity.deleted_by == user_id
    
    def test_restore(self):
        """Test restoring soft-deleted entity."""
        entity = SoftDeletableEntity()
        entity.soft_delete(by_user=uuid4())
        
        entity.restore()
        
        assert entity.is_deleted is False
        assert entity.deleted_at is None
        assert entity.deleted_by is None
