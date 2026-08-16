package com.spring.crud.demo.aop;


import com.spring.crud.demo.model.SportsIcon;
import com.spring.crud.demo.model.Student;
import com.spring.crud.demo.model.emp.Employee;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;

import java.util.Objects;

@Slf4j
@Aspect
@AutoConfiguration
@Component
public class LoggerAspect {

    @Before("@annotation(com.spring.crud.demo.annotation.LogObjectBefore)")
    public void logSportsIconBefore(JoinPoint joinPoint) {
        Object[] args = joinPoint.getArgs();
        for (Object arg : args) {
            if (arg instanceof SportsIcon sportsIcon) {
                log.info("******* Sports Icon before :: {}", sportsIcon);
            } else if (arg instanceof Employee employee) {
                log.info("******* Employee before :: {}", employee);
            } else if (arg instanceof Student student) {
                log.info("******* Student before :: {}", student);
            }
        }
    }

    @AfterReturning(value = "@annotation(com.spring.crud.demo.annotation.LogObjectAfter)", returning = "result")
    public void logSportsIconAfter(JoinPoint joinPoint, Object result) {
        Object[] args = joinPoint.getArgs();
        if (Objects.nonNull(result)) {
            if (result instanceof ResponseEntity responseEntity) {

                if (responseEntity.getStatusCode().value() == 200)
                    log.info("******* Returning object :: {}", responseEntity.getBody());
                else
                    log.error("Something went wrong while logging...!");
            }
        }
    }
}
