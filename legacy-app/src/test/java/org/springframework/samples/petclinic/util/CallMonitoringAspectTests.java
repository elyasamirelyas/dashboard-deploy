package org.springframework.samples.petclinic.util;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.Field;

import org.junit.jupiter.api.Test;

/**
 * Plain JUnit 5 unit tests for {@link CallMonitoringAspect}.
 *
 * This class is annotated with @Aspect, so the automated test-generation
 * agent in this project's pipeline (agents/test_generation_agent.py) skips
 * it forever - any class carrying a Spring/AspectJ stereotype annotation is
 * excluded on purpose, because exercising it properly would need a live
 * AOP-woven Spring context, not a plain unit test. Before this file it had
 * 0% line coverage. Writing it by hand is exactly the "go beyond what the
 * pipeline can do on its own" case for this project.
 *
 * Scope: only the plain-Java parts of the aspect are tested here -
 * isEnabled/setEnabled, reset(), getCallCount(), and both branches of
 * getCallTime(). The advice method invoke(ProceedingJoinPoint) is
 * deliberately NOT tested: it requires a real AspectJ ProceedingJoinPoint
 * produced by actual AOP weaving around a @Repository bean, which is a
 * Spring-context-level concern, not something a plain JUnit 5 test should
 * fake. That is consistent with why the automated pipeline never picks this
 * class in the first place.
 *
 * callCount / accumulatedCallTime have no public mutators other than
 * invoke() and reset() - reset() only ever sets them to zero. To exercise
 * the averaging branch of getCallTime() (accumulatedCallTime / callCount)
 * we need a non-zero callCount, so this test sets those two private fields
 * directly via reflection. That is an honest way to test the pure
 * arithmetic in getCallTime() in isolation, without pretending to fake AOP
 * weaving with a hand-rolled ProceedingJoinPoint.
 */
class CallMonitoringAspectTests {

    @Test
    void shouldBeEnabledByDefault() {
        CallMonitoringAspect aspect = new CallMonitoringAspect();

        assertThat(aspect.isEnabled()).isTrue();
    }

    @Test
    void shouldAllowDisablingAndReEnabling() {
        CallMonitoringAspect aspect = new CallMonitoringAspect();

        aspect.setEnabled(false);
        assertThat(aspect.isEnabled()).isFalse();

        aspect.setEnabled(true);
        assertThat(aspect.isEnabled()).isTrue();
    }

    @Test
    void newAspectShouldHaveZeroCallCount() {
        CallMonitoringAspect aspect = new CallMonitoringAspect();

        assertThat(aspect.getCallCount()).isZero();
    }

    @Test
    void getCallTimeShouldReturnZeroWhenNoCallsRecorded() {
        // this is the divide-by-zero guard in getCallTime():
        // callCount == 0 must short-circuit to 0 instead of dividing.
        CallMonitoringAspect aspect = new CallMonitoringAspect();

        assertThat(aspect.getCallCount()).isZero();
        assertThat(aspect.getCallTime()).isZero();
    }

    @Test
    void getCallTimeShouldAverageAccumulatedTimeOverCallCount() throws Exception {
        CallMonitoringAspect aspect = new CallMonitoringAspect();

        setPrivateField(aspect, "callCount", 4);
        setPrivateField(aspect, "accumulatedCallTime", 200L);

        assertThat(aspect.getCallCount()).isEqualTo(4);
        assertThat(aspect.getCallTime()).isEqualTo(50L); // 200 / 4
    }

    @Test
    void resetShouldZeroOutCallCountAndAccumulatedTime() throws Exception {
        CallMonitoringAspect aspect = new CallMonitoringAspect();
        setPrivateField(aspect, "callCount", 7);
        setPrivateField(aspect, "accumulatedCallTime", 999L);

        aspect.reset();

        assertThat(aspect.getCallCount()).isZero();
        assertThat(aspect.getCallTime()).isZero();
    }

    private static void setPrivateField(Object target, String fieldName, Object value) throws Exception {
        Field field = target.getClass().getDeclaredField(fieldName);
        field.setAccessible(true);
        field.set(target, value);
    }
}