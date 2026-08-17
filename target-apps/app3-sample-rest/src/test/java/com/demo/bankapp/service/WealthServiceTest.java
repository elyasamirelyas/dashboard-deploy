package com.demo.bankapp.service;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mockito;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import com.demo.bankapp.exception.BadRequestException;
import com.demo.bankapp.exception.InsufficientFundsException;
import com.demo.bankapp.model.Wealth;
import com.demo.bankapp.repository.WealthRepository;
import com.demo.bankapp.service.concretions.WealthService;
@ExtendWith(SpringExtension.class)
public class WealthServiceTest {
        @MockBean
        private WealthRepository repository;
        private WealthService service;
        private Wealth mockedWealth;
        private Long mockedUserId;
        @BeforeEach
        public void setUp() {
                service = new WealthService(repository) {
                        @Override
                        public Map<String, Double> getCurrencyRates() {
                                Map<String, Double> mockedRates = new HashMap<>();
                                mockedRates.put("USD", 0.1);
                                mockedRates.put("EUR", 0.09);
                                mockedRates.put("TRY", 1.0);
                                mockedRates.put("AUD", 0.15);
                                return mockedRates;
                        }
                };
                Map<String, BigDecimal> mockedWealthMap = new HashMap<>();
                mockedWealthMap.put("USD", BigDecimal.valueOf(2500));
                mockedWealthMap.put("TRY", BigDecimal.valueOf(2000));
                mockedWealthMap.put("EUR", BigDecimal.valueOf(3000));
                mockedWealthMap.put("AUD", BigDecimal.ZERO);
                this.mockedUserId = 5125L;
                this.mockedWealth = new Wealth(mockedUserId, mockedWealthMap);
                Mockito.when(repository.findById(mockedUserId)).thenReturn(Optional.of(mockedWealth));
        }
        @Test
        public void newWealthRecord() {
                service.newWealthRecord(25161L);
        }
        @Test
        public void makeWealthExchange() {
                service.makeWealthExchange(mockedUserId, "USD", BigDecimal.valueOf(150), true);
                service.makeWealthExchange(mockedUserId, "USD", BigDecimal.valueOf(250), false);
        }
        @Test
        public void makeWealthExchange_InsufficientFunds_Sell() {
                assertThrows(InsufficientFundsException.class, () ->
                        service.makeWealthExchange(mockedUserId, "USD", BigDecimal.valueOf(3000), false));
        }
        @Test
        public void makeWealthExchange_InsufficientFunds_Buy() {
                assertThrows(InsufficientFundsException.class, () ->
                        service.makeWealthExchange(mockedUserId, "USD", BigDecimal.valueOf(3000), true));
        }
        @Test
        public void makeWealthExchange_InvalidCurrency() {
                assertThrows(BadRequestException.class, () ->
                        service.makeWealthExchange(mockedUserId, "XSD", BigDecimal.valueOf(250), false));
        }
        @Test
        public void makeWealthTransaction() {
                service.makeWealthTransaction(mockedUserId, "EUR", BigDecimal.valueOf(2516), true);
                service.makeWealthTransaction(mockedUserId, "TRY", BigDecimal.valueOf(1000), false);
        }
        @Test
        public void makeWealthTransaction_InsufficientFunds() {
                assertThrows(InsufficientFundsException.class, () ->
                        service.makeWealthTransaction(mockedUserId, "TRY", BigDecimal.valueOf(5000), false));
        }
        @Test
        public void makeWealthTransaction_InvalidCurrency() {
                assertThrows(BadRequestException.class, () ->
                        service.makeWealthTransaction(mockedUserId, "DTD", BigDecimal.valueOf(250), false));
        }
        @Test
        public void findWealth() {
                service.findWealth(mockedUserId);
        }
}