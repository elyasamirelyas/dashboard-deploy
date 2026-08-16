package com.demo.bankapp.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mockito;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.junit.jupiter.SpringExtension;

import com.demo.bankapp.model.Transfer;
import com.demo.bankapp.repository.TransferRepository;
import com.demo.bankapp.service.concretions.TransferService;

@ExtendWith(SpringExtension.class)
public class TransferServiceTest {
	
	@MockBean
	private TransferRepository repository;
	
	private TransferService service;
	
	@BeforeEach
	public void setUp() {
		service = new TransferService(repository);
	}
	
	@Test
	public void createNewTransaction() {
		Transfer mockedTransfer = new Transfer(5816L, 2181L, "AUD", BigDecimal.valueOf(25125));
		Mockito.when(repository.save(Mockito.any())).thenReturn(mockedTransfer);
		
		Transfer createdTransfer = service.createNewTransfer(mockedTransfer);
		
		assertThat(createdTransfer.getAmount()).isEqualTo(mockedTransfer.getAmount());
		assertThat(createdTransfer.getCurrency()).isEqualTo(mockedTransfer.getCurrency());
		assertThat(createdTransfer.getFromUserId()).isEqualTo(mockedTransfer.getFromUserId());
		assertThat(createdTransfer.getToUserId()).isEqualTo(mockedTransfer.getToUserId());
	}
	
	@Test 
	public void findAllTransfersFrom24Hours() {
		List<Transfer> mockedTransferList = new ArrayList<>();
		Transfer mockedTransfer = new Transfer(5816L, 2181L, "AUD", BigDecimal.valueOf(25125));
		mockedTransferList.add(mockedTransfer);
		
		Mockito.when(repository.findAllTransfersFrom24Hours(mockedTransfer.getFromUserId())).thenReturn(mockedTransferList);
		List<Transfer> foundTransferList = service.findAllTransfersFrom24Hours(mockedTransfer.getFromUserId());
		
		assertThat(foundTransferList).isEqualTo(mockedTransferList);
	}

}
