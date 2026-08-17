package com.bezkoder.spring.jpa.h2.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;

public class TutorialTests {

    private Tutorial tutorial;

    @BeforeEach
    public void setUp() {
        tutorial = new Tutorial();
    }

    @Test
    public void testDefaultConstructor() {
        Tutorial t = new Tutorial();
        assertNotNull(t);
        assertEquals(0, t.getId());
        assertNull(t.getTitle());
        assertNull(t.getDescription());
        assertFalse(t.isPublished());
    }

    @Test
    public void testParameterizedConstructor() {
        Tutorial t = new Tutorial("Spring Boot Tutorial", "Learn Spring Boot", true);
        assertNotNull(t);
        assertEquals("Spring Boot Tutorial", t.getTitle());
        assertEquals("Learn Spring Boot", t.getDescription());
        assertTrue(t.isPublished());
    }

    @Test
    public void testParameterizedConstructorWithNullValues() {
        Tutorial t = new Tutorial(null, null, false);
        assertNotNull(t);
        assertNull(t.getTitle());
        assertNull(t.getDescription());
        assertFalse(t.isPublished());
    }

    @Test
    public void testSetAndGetTitle() {
        tutorial.setTitle("JPA Tutorial");
        assertEquals("JPA Tutorial", tutorial.getTitle());
    }

    @Test
    public void testSetTitleWithNull() {
        tutorial.setTitle("Initial Title");
        tutorial.setTitle(null);
        assertNull(tutorial.getTitle());
    }

    @Test
    public void testSetAndGetDescription() {
        tutorial.setDescription("This is a description");
        assertEquals("This is a description", tutorial.getDescription());
    }

    @Test
    public void testSetDescriptionWithNull() {
        tutorial.setDescription("Initial Description");
        tutorial.setDescription(null);
        assertNull(tutorial.getDescription());
    }

    @Test
    public void testSetAndGetPublished() {
        tutorial.setPublished(true);
        assertTrue(tutorial.isPublished());
        
        tutorial.setPublished(false);
        assertFalse(tutorial.isPublished());
    }

    @Test
    public void testGetId() {
        assertEquals(0, tutorial.getId());
    }

    @Test
    public void testToString() {
        Tutorial t = new Tutorial("Test Title", "Test Description", true);
        String result = t.toString();
        
        assertNotNull(result);
        assertTrue(result.contains("Tutorial"));
        assertTrue(result.contains("id="));
        assertTrue(result.contains("title=Test Title"));
        assertTrue(result.contains("desc=Test Description"));
        assertTrue(result.contains("published=true"));
    }

    @Test
    public void testToStringWithNullFields() {
        Tutorial t = new Tutorial(null, null, false);
        String result = t.toString();
        
        assertNotNull(result);
        assertTrue(result.contains("Tutorial"));
        assertTrue(result.contains("title=null"));
        assertTrue(result.contains("desc=null"));
        assertTrue(result.contains("published=false"));
    }

    @Test
    public void testSetMultipleFields() {
        tutorial.setTitle("Complete Tutorial");
        tutorial.setDescription("Complete Description");
        tutorial.setPublished(true);
        
        assertEquals("Complete Tutorial", tutorial.getTitle());
        assertEquals("Complete Description", tutorial.getDescription());
        assertTrue(tutorial.isPublished());
    }

    @Test
    public void testEmptyStringValues() {
        tutorial.setTitle("");
        tutorial.setDescription("");
        
        assertEquals("", tutorial.getTitle());
        assertEquals("", tutorial.getDescription());
    }
}