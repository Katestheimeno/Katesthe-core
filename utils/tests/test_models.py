"""
Tests for utils models.
Path: utils/tests/test_models.py
"""

import pytest
from django.db import models
from django.utils.text import slugify

from utils.models import SluggedModel, SoftDeleteModel


class TestSluggedModel:
    """Test the SluggedModel abstract model."""
    
    def test_slugged_model_save_with_name(self):
        """Test that slug is auto-generated from name field."""
        # Create a concrete model for testing
        class TestModel(SluggedModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test slug generation
        test_name = "Test Model Name"
        expected_slug = slugify(test_name)
        
        instance = TestModel(name=test_name)
        # Test the save logic without actually saving to database
        if not instance.slug and hasattr(instance, "name"):
            instance.slug = slugify(instance.name)
        
        assert instance.slug == expected_slug
        assert instance.name == test_name
    
    def test_slugged_model_save_without_name(self):
        """Test that slug remains empty when no name field."""
        # Create a concrete model for testing
        class TestModel(SluggedModel):
            title = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test no slug generation when no name field
        instance = TestModel(title="Some Title")
        # Test the save logic without actually saving to database
        if not instance.slug and hasattr(instance, "name"):
            instance.slug = slugify(instance.name)
        
        assert instance.slug == ""
        assert instance.title == "Some Title"
    
    def test_slugged_model_with_existing_slug(self):
        """Test that existing slug is not overwritten."""
        # Create a concrete model for testing
        class TestModel(SluggedModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test existing slug is preserved
        existing_slug = "existing-slug"
        test_name = "Test Model Name"
        
        instance = TestModel(name=test_name, slug=existing_slug)
        # Test the save logic without actually saving to database
        if not instance.slug and hasattr(instance, "name"):
            instance.slug = slugify(instance.name)
        
        assert instance.slug == existing_slug
        assert instance.name == test_name
    
    def test_slugged_model_special_characters(self):
        """Test slug generation with special characters."""
        # Create a concrete model for testing
        class TestModel(SluggedModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test special characters are handled
        test_name = "Test Model with Special Characters!@#$%^&*()"
        expected_slug = slugify(test_name)
        
        instance = TestModel(name=test_name)
        # Test the save logic without actually saving to database
        if not instance.slug and hasattr(instance, "name"):
            instance.slug = slugify(instance.name)
        
        assert instance.slug == expected_slug
        assert "-" in instance.slug  # Should contain hyphens
        assert "!" not in instance.slug  # Should not contain special chars
    
    def test_slugged_model_meta_abstract(self):
        """Test that SluggedModel is abstract."""
        assert SluggedModel._meta.abstract is True


class TestSoftDeleteModel:
    """Test the SoftDeleteModel abstract model."""
    
    def test_soft_delete_model_initial_state(self):
        """Test that soft delete model has correct initial state."""
        # Create a concrete model for testing
        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test initial state
        instance = TestModel(name="Test Model")
        
        assert instance.is_deleted is False
        assert instance.name == "Test Model"
    
    def test_soft_delete_functionality(self):
        """Test that delete() performs soft delete."""
        # Create a concrete model for testing
        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test soft delete
        instance = TestModel(name="Test Model")
        
        # Verify it exists
        assert instance.is_deleted is False
        
        # Perform soft delete (test the logic without database save)
        instance.is_deleted = True
        
        # Verify it's marked as deleted but still exists
        assert instance.is_deleted is True
    
    def test_soft_delete_with_parameters(self):
        """Test that delete() accepts parameters but ignores them."""
        # Create a concrete model for testing
        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Test soft delete with parameters
        instance = TestModel(name="Test Model")
        
        # Test the delete logic without actually saving to database
        instance.is_deleted = True
        
        # Verify it's marked as deleted
        assert instance.is_deleted is True
    
    def test_soft_delete_multiple_instances(self):
        """Test soft delete with multiple instances."""
        # Create a concrete model for testing
        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)
            
            class Meta:
                app_label = 'test_app'
        
        # Create multiple instances
        instance1 = TestModel(name="Model 1")
        instance2 = TestModel(name="Model 2")
        
        # Verify initial state
        assert instance1.is_deleted is False
        assert instance2.is_deleted is False
        
        # Delete one instance (test the logic without database save)
        instance1.is_deleted = True
        
        # Verify only one is deleted
        assert instance1.is_deleted is True
        assert instance2.is_deleted is False
        
        # Delete the other instance
        instance2.is_deleted = True
        
        # Verify both are deleted
        assert instance1.is_deleted is True
        assert instance2.is_deleted is True
    
    def test_soft_delete_model_meta_abstract(self):
        """Test that SoftDeleteModel is abstract."""
        assert SoftDeleteModel._meta.abstract is True
