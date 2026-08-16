package com.iamvickyav.springboot.SpringBootRestWithH2.model;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class EmployeeTests {

    @Test
    void testGetAndSetId() {
        Employee employee = new Employee();
        Integer expectedId = 123;
        
        employee.setId(expectedId);
        Integer actualId = employee.getId();
        
        assertEquals(expectedId, actualId);
    }

    @Test
    void testGetAndSetName() {
        Employee employee = new Employee();
        String expectedName = "John Doe";
        
        employee.setName(expectedName);
        String actualName = employee.getName();
        
        assertEquals(expectedName, actualName);
    }

    @Test
    void testSetIdWithNull() {
        Employee employee = new Employee();
        
        employee.setId(null);
        Integer actualId = employee.getId();
        
        assertNull(actualId);
    }

    @Test
    void testSetNameWithNull() {
        Employee employee = new Employee();
        
        employee.setName(null);
        String actualName = employee.getName();
        
        assertNull(actualName);
    }

    @Test
    void testSetNameWithEmptyString() {
        Employee employee = new Employee();
        String expectedName = "";
        
        employee.setName(expectedName);
        String actualName = employee.getName();
        
        assertEquals(expectedName, actualName);
    }

    @Test
    void testEmployeeInitialState() {
        Employee employee = new Employee();
        
        assertNull(employee.getId());
        assertNull(employee.getName());
    }

    @Test
    void testSetMultipleFields() {
        Employee employee = new Employee();
        Integer expectedId = 456;
        String expectedName = "Jane Smith";
        
        employee.setId(expectedId);
        employee.setName(expectedName);
        
        assertEquals(expectedId, employee.getId());
        assertEquals(expectedName, employee.getName());
    }

    @Test
    void testSetIdWithZero() {
        Employee employee = new Employee();
        Integer expectedId = 0;
        
        employee.setId(expectedId);
        Integer actualId = employee.getId();
        
        assertEquals(expectedId, actualId);
    }

    @Test
    void testSetIdWithNegativeValue() {
        Employee employee = new Employee();
        Integer expectedId = -1;
        
        employee.setId(expectedId);
        Integer actualId = employee.getId();
        
        assertEquals(expectedId, actualId);
    }

    @Test
    void testOverwriteExistingValues() {
        Employee employee = new Employee();
        
        employee.setId(100);
        employee.setName("First Name");
        
        employee.setId(200);
        employee.setName("Second Name");
        
        assertEquals(200, employee.getId());
        assertEquals("Second Name", employee.getName());
    }
}