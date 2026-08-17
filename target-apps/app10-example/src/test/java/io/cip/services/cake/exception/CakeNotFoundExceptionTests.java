package io.cip.services.cake.exception;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class CakeNotFoundExceptionTests {

    @Test
    void testCakeNotFoundExceptionCanBeThrown() {
        assertThrows(CakeNotFoundException.class, () -> {
            throw new CakeNotFoundException();
        });
    }

    @Test
    void testCakeNotFoundExceptionIsRuntimeException() {
        CakeNotFoundException exception = new CakeNotFoundException();
        assertTrue(exception instanceof RuntimeException);
    }

    @Test
    void testCakeNotFoundExceptionCanBeCaught() {
        try {
            throw new CakeNotFoundException();
        } catch (CakeNotFoundException e) {
            assertNotNull(e);
            assertTrue(e instanceof CakeNotFoundException);
        }
    }

    @Test
    void testCakeNotFoundExceptionHasNoMessage() {
        CakeNotFoundException exception = new CakeNotFoundException();
        assertNull(exception.getMessage());
    }

    @Test
    void testCakeNotFoundExceptionHasNoCause() {
        CakeNotFoundException exception = new CakeNotFoundException();
        assertNull(exception.getCause());
    }
}