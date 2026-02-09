package com.ing.backend.aop;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.*;
import org.aspectj.lang.reflect.CodeSignature;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;

@Component
@Aspect
@Slf4j
public class ControllerLogger {
    private static String trackKey = "track-id";

    @Pointcut("within(com.ing.backend.controller..*)")
    public void controllers() {}

    @Pointcut("execution(public * * (..))")
    public void publicMethod() {}

    @Before("controllers() && publicMethod()")
    public void logEnter(JoinPoint joinPoint) {
        MDC.put(trackKey, UUID.randomUUID().toString());
        log.info("{} - Called with: {}", pointInfo(joinPoint), extractParameters(joinPoint));
    }

    @AfterReturning(value = "controllers() && publicMethod()", returning = "retVal")
    public void logResult(JoinPoint joinPoint, Object retVal) {
        log.info("{} - Respond with: {}", pointInfo(joinPoint), retVal);
    }

    @AfterThrowing(value = "controllers() && publicMethod()", throwing = "failure")
    public void logException(JoinPoint joinPoint, Throwable failure) {
        log.warn("{} - Failed with: {}", pointInfo(joinPoint), extractFailure(failure));
    }

    @After("controllers() && publicMethod()")
    public void clearLog() {
        MDC.remove(trackKey);
    }

    private String pointInfo(JoinPoint joinPoint) {
        return "[%s] : [%s]".formatted(MDC.get(trackKey), pointName(joinPoint));
    }

    private String pointName(JoinPoint joinPoint) {
        return "%s#%s".formatted(joinPoint.getSignature().getDeclaringType().getSimpleName(), joinPoint.getSignature().getName());
    }

    private String extractParameters(JoinPoint joinPoint) {
        List<String> values = Arrays.stream(joinPoint.getArgs()).map(this::extractParameter).toList();

        if (values.isEmpty()) {
            return "NO PARAMS";
        }

        List<String> parameters = Arrays.stream(((CodeSignature)joinPoint.getSignature()).getParameterNames()).toList();

        return String.join(", ", parameters.stream().map(name -> "%s : %s".formatted(name, values.get(parameters.indexOf(name)))).toList());
    }

    private String extractParameter(Object value) {
        return switch (value) {
            case null ->  "[null]";
            case String s -> s;
            case UUID u -> u.toString();
            default -> "[%s]".formatted(value.getClass().getSimpleName());
        };
    }

    private String extractFailure(Throwable t) {
        if (t.getCause() != null) {
            return extractFailure(t.getCause()) + (t.getMessage() != null ? t.getMessage() : ":shrug:");
        }

        return t.getMessage();
    }
}
