package org.springframework.samples.petclinic.util;

import java.util.ArrayList;
import java.util.Collection;

import org.junit.jupiter.api.Test;
import org.springframework.orm.ObjectRetrievalFailureException;
import org.springframework.samples.petclinic.model.BaseEntity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class EntityUtilsTests {

    private static class TestEntity extends BaseEntity {
        public TestEntity(Integer id) {
            this.id = id;
        }
    }

    @Test
    void testGetByIdFound() {
        Collection<TestEntity> entities = new ArrayList<>();
        TestEntity entity1 = new TestEntity(1);
        TestEntity entity2 = new TestEntity(2);
        TestEntity entity3 = new TestEntity(3);
        
        entities.add(entity1);
        entities.add(entity2);
        entities.add(entity3);
        
        TestEntity result = EntityUtils.getById(entities, TestEntity.class, 2);
        
        assertNotNull(result);
        assertEquals(2, result.getId());
        assertEquals(entity2, result);
    }

    @Test
    void testGetByIdNotFound() {
        Collection<TestEntity> entities = new ArrayList<>();
        TestEntity entity1 = new TestEntity(1);
        TestEntity entity2 = new TestEntity(2);
        
        entities.add(entity1);
        entities.add(entity2);
        
        assertThrows(ObjectRetrievalFailureException.class, () -> {
            EntityUtils.getById(entities, TestEntity.class, 99);
        });
    }

    @Test
    void testGetByIdEmptyCollection() {
        Collection<TestEntity> entities = new ArrayList<>();
        
        assertThrows(ObjectRetrievalFailureException.class, () -> {
            EntityUtils.getById(entities, TestEntity.class, 1);
        });
    }
}