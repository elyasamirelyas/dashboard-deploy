package com.spring.crud.demo.config.error;

import com.spring.crud.demo.config.CustomException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import static org.junit.jupiter.api.Assertions.assertThrows;

@ExtendWith(SpringExtension.class)
public class CustomExceptionTest {
    private static final Logger log = LoggerFactory.getLogger(CustomExceptionTest.class);

    @Test
    public void CustomExceptionTestWithoutParams() {
        assertThrows(CustomException.class, () -> {
            log.info("Throw Base CustomException");
            throw new CustomException();
        });
    }

    @Test
    public void CustomExceptionTestWitMessage() {
        assertThrows(CustomException.class, () -> {
            log.info("Throw CustomException WitMessage");
            throw new CustomException("Error");
        });
    }

    @Test
    public void CustomExceptionTestWitMessageAndThrowable() {
        assertThrows(CustomException.class, () -> {
            log.info("Throw CustomException Wit Message and Throwable");
            throw new CustomException("Error", new CustomException());
        });
    }
    @Test
    public void CustomExceptionTestWithThrowable() {
        assertThrows(CustomException.class, () -> {
            log.info("Throw CustomException With Throwable");
            throw new CustomException(new CustomException());
        });
    }

    @Test
    public void CustomExceptionTestWitMessageAndThrowableBooleans() {
        assertThrows(CustomException.class, () -> {
            log.info("Throw CustomException With Message, Throwable and Booleans");
            throw new CustomException("Error", new CustomException(), true, true);
        });
    }
}
