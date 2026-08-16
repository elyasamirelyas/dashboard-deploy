package org.springframework.samples.petclinic.security;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.samples.petclinic.PetClinicApplication;
import org.springframework.test.web.servlet.MockMvc;

/**
 * End-to-end security test for {@link DisableSecurityConfig}.
 *
 * Every other test in this suite uses MockMvcBuilders.standaloneSetup(...),
 * which builds MockMvc directly around a single @Controller bean and never
 * constructs the servlet filter chain. Spring Security lives entirely in
 * that filter chain, so none of the existing tests ever exercise it -
 * that's exactly why DisableSecurityConfig sat at 0% line coverage.
 *
 * On top of that, src/test/resources/application.properties sets
 * petclinic.security.enable=true, which - via DisableSecurityConfig's
 * @ConditionalOnProperty(havingValue = "false") - means its filterChain()
 * bean is never even constructed during the normal test run, regardless of
 * MockMvc setup style.
 *
 * @AutoConfigureMockMvc builds MockMvc against the REAL application
 * context (not a standalone single controller), so the real Spring
 * Security filter chain actually runs on every request - and because
 * spring-security-test is on the classpath, it's automatically wired in.
 * We override petclinic.security.enable=false for just this test class,
 * which is the app's real production default (see
 * src/main/resources/application.properties), so DisableSecurityConfig's
 * bean is the one that gets built and exercised here.
 */
@SpringBootTest(
    classes = PetClinicApplication.class,
    properties = "petclinic.security.enable=false"
)
@AutoConfigureMockMvc
class DisableSecurityConfigTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void unauthenticatedRequestShouldBePermittedWhenSecurityDisabled() throws Exception {
        // No auth of any kind. If DisableSecurityConfig's permitAll() were
        // NOT actually wired in, this would come back 401/403 instead.
        this.mockMvc.perform(get("/api/owners"))
            .andExpect(status().isOk());
    }

    @Test
    void postWithoutCsrfTokenShouldNotBeBlockedByCsrfProtection() throws Exception {
        // Spring Security's default CSRF filter rejects state-changing
        // requests with no token (403 "Invalid CSRF Token"). We send no
        // token at all here. If DisableSecurityConfig's csrf().disable()
        // were NOT actually applied, this would come back 403 regardless of
        // the body's validity.
        String validOwnerJson = "{"
            + "\"firstName\":\"Integration\","
            + "\"lastName\":\"TestOwner\","
            + "\"address\":\"1 Test Way\","
            + "\"city\":\"Glasgow\","
            + "\"telephone\":\"1234567890\""
            + "}";

        this.mockMvc.perform(post("/api/owners")
                .content(validOwnerJson)
                .contentType(MediaType.APPLICATION_JSON_VALUE)
                .accept(MediaType.APPLICATION_JSON_VALUE))
            .andExpect(status().isCreated());
    }
}