package com.demo.bankapp.controller;

import static org.hamcrest.Matchers.equalTo;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.RequestBuilder;
import org.springframework.test.web.servlet.ResultActions;
import org.springframework.test.web.servlet.result.MockMvcResultMatchers;

import com.demo.bankapp.config.TestUtils;
import com.demo.bankapp.model.User;
import com.demo.bankapp.model.Wealth;
import com.demo.bankapp.request.RetrieveWealthRequest;
import com.demo.bankapp.service.abstractions.IUserService;
import com.demo.bankapp.service.abstractions.IWealthService;
import com.fasterxml.jackson.databind.ObjectMapper;

@WebMvcTest(WealthController.class)
@AutoConfigureMockMvc(addFilters = false)
public class WealthControllerTest {
	
	@MockBean
	private IUserService userService;

	@MockBean
	private IWealthService wealthService;
	
	@Autowired
	private MockMvc mockMvc;
	
	private RetrieveWealthRequest request;

	public void initWealthControllerTest(RetrieveWealthRequest request) {
		this.request = request;
	}
	
	public static List<RetrieveWealthRequest> data() {
		RetrieveWealthRequest request1 = new RetrieveWealthRequest();
		RetrieveWealthRequest request2 = new RetrieveWealthRequest();
		request2.setUsername("");
		RetrieveWealthRequest request3 = new RetrieveWealthRequest();
		request3.setUsername("Mert");
		
		List<RetrieveWealthRequest> testCases = new ArrayList<>();
		testCases.add(request1);
		testCases.add(request2);
		testCases.add(request3);
		
		return testCases;
	}

	@MethodSource("data")
	@ParameterizedTest
	public void retrieveWealth(RetrieveWealthRequest request) throws Exception {

		initWealthControllerTest(request);
		
		boolean shouldThrowBadRequest = request.getUsername() == null || request.getUsername().equals("");
		
		Map<String, BigDecimal> mockedWealthMap = new HashMap<>();
		mockedWealthMap.put("TRY", BigDecimal.valueOf(58212));
		mockedWealthMap.put("EUR", BigDecimal.valueOf(5000));
		mockedWealthMap.put("USD", BigDecimal.valueOf(1000));
		
		Mockito.when(userService.findByUserName(Mockito.anyString())).thenReturn(new User(request.getUsername(), "mert123", "52812576921"));
		Mockito.when(wealthService.findWealth(Mockito.any())).thenReturn(new Wealth(5125L, mockedWealthMap));
		
		String requestAsJson = new ObjectMapper().writeValueAsString(request);
		RequestBuilder requestBuilder = TestUtils.getPostRequestBuilder("/wealth/retrieve", requestAsJson);
		
		ResultActions resultActions = mockMvc.perform(requestBuilder);
		if(shouldThrowBadRequest) {
			resultActions.andExpect(MockMvcResultMatchers.status().isBadRequest());
		} else {
			resultActions.andExpect(MockMvcResultMatchers.status().isOk())
			.andExpect(jsonPath("$.wealth.userId", equalTo(5125)))
			.andExpect(jsonPath("$.wealth.wealthMap.TRY", equalTo(58212)))
			.andExpect(jsonPath("$.wealth.wealthMap.EUR", equalTo(5000)))
			.andExpect(jsonPath("$.wealth.wealthMap.USD", equalTo(1000)));
		}
	}

}