package org.springframework.samples.petclinic.rest;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.samples.petclinic.service.ClinicService;
import org.springframework.samples.petclinic.service.clinicService.ApplicationTestConfig;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.web.WebAppConfiguration;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * Tests the actual JSON body content of ExceptionControllerAdvice's error
 * responses, not just their HTTP status code.
 *
 * Every existing REST test that hits a bad-request/not-found path only
 * asserts status() - none of them ever look at what's actually in the
 * response body for the catch-all Exception.class handler path. This class
 * closes that gap for two realistic client mistakes: an invalid path
 * variable, and malformed JSON.
 *
 * FINDING (documented, not silently "fixed" - that's a design decision for
 * you to make, not mine to make for you): ExceptionControllerAdvice maps
 * EVERY uncaught exception to HTTP 400 Bad Request, including exceptions
 * that would actually be caused by a server-side bug rather than bad client
 * input (e.g. a NullPointerException deep in a service method would also
 * come back as 400). Per the PDF's guidance on informative vs. misleading
 * error messages: a 400 tells the API caller "you sent something wrong",
 * which is accurate for the two cases below, but would be misleading for a
 * genuine server-side fault - a caller has no way to distinguish "fix your
 * request" from "this is our bug" from the status code alone. A more
 * informative implementation would only route validation/parsing
 * exceptions to 400 and let unexpected exceptions surface as 500.
 */
@SpringBootTest
@ContextConfiguration(classes = ApplicationTestConfig.class)
@WebAppConfiguration
class ExceptionControllerAdviceErrorFormatTests {

    @Autowired
    private OwnerRestController ownerRestController;

    @MockBean
    private ClinicService clinicService;

    private MockMvc mockMvc;

    @BeforeEach
    void setup() {
        this.mockMvc = MockMvcBuilders.standaloneSetup(ownerRestController)
            .setControllerAdvice(new ExceptionControllerAdvice())
            .build();
    }

    @Test
    void invalidPathVariableTypeShouldReturnInformativeErrorBody() throws Exception {
        // ownerId is declared as `int` on the controller method, so a
        // non-numeric path segment fails Spring's argument conversion
        // before the controller body ever runs, and falls through to
        // ExceptionControllerAdvice's catch-all handler.
        this.mockMvc.perform(get("/api/owners/not-a-number")
                .accept(MediaType.APPLICATION_JSON_VALUE))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.className").exists())
            .andExpect(jsonPath("$.exMessage").exists());
    }

    @Test
    void malformedJsonBodyShouldReturnInformativeErrorBody() throws Exception {
        this.mockMvc.perform(post("/api/owners/")
                .content("{ this is not valid json")
                .contentType(MediaType.APPLICATION_JSON_VALUE)
                .accept(MediaType.APPLICATION_JSON_VALUE))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.className").exists())
            .andExpect(jsonPath("$.exMessage").exists());
    }
}