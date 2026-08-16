package com.example.rjany.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;

public class StudentTests {

    private Student student;

    @BeforeEach
    public void setUp() {
        student = new Student();
    }

    @Test
    public void testSetAndGetId() {
        Long expectedId = 1L;
        student.setId(expectedId);
        assertEquals(expectedId, student.getId());
    }

    @Test
    public void testSetAndGetName() {
        String expectedName = "John Doe";
        student.setName(expectedName);
        assertEquals(expectedName, student.getName());
    }

    @Test
    public void testSetAndGetAge() {
        Integer expectedAge = 25;
        student.setAge(expectedAge);
        assertEquals(expectedAge, student.getAge());
    }

    @Test
    public void testSetAndGetEmail() {
        String expectedEmail = "john.doe@example.com";
        student.setEmail(expectedEmail);
        assertEquals(expectedEmail, student.getEmail());
    }

    @Test
    public void testStudentWithAllProperties() {
        Long id = 100L;
        String name = "Jane Smith";
        Integer age = 22;
        String email = "jane.smith@example.com";

        student.setId(id);
        student.setName(name);
        student.setAge(age);
        student.setEmail(email);

        assertEquals(id, student.getId());
        assertEquals(name, student.getName());
        assertEquals(age, student.getAge());
        assertEquals(email, student.getEmail());
    }

    @Test
    public void testStudentWithNullValues() {
        student.setId(null);
        student.setName(null);
        student.setAge(null);
        student.setEmail(null);

        assertNull(student.getId());
        assertNull(student.getName());
        assertNull(student.getAge());
        assertNull(student.getEmail());
    }

    @Test
    public void testDefaultConstructorInitializesWithNullValues() {
        Student newStudent = new Student();
        assertNull(newStudent.getId());
        assertNull(newStudent.getName());
        assertNull(newStudent.getAge());
        assertNull(newStudent.getEmail());
    }

    @Test
    public void testSetAgeWithZero() {
        Integer zeroAge = 0;
        student.setAge(zeroAge);
        assertEquals(zeroAge, student.getAge());
    }

    @Test
    public void testSetAgeWithNegativeValue() {
        Integer negativeAge = -5;
        student.setAge(negativeAge);
        assertEquals(negativeAge, student.getAge());
    }

    @Test
    public void testSetEmptyStringName() {
        String emptyName = "";
        student.setName(emptyName);
        assertEquals(emptyName, student.getName());
    }

    @Test
    public void testSetEmptyStringEmail() {
        String emptyEmail = "";
        student.setEmail(emptyEmail);
        assertEquals(emptyEmail, student.getEmail());
    }
}