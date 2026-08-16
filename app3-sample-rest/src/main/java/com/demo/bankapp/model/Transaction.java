package com.demo.bankapp.model;

import java.math.BigDecimal;
import java.util.Date;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;

import lombok.Data;

@Data
@Entity
public class Transaction {

	private @Id @GeneratedValue Long id;
	private Long userId;
	private boolean isBought;
	private String currency;
	private BigDecimal amount;
	private Date transactionTime;

	private Transaction() {
	}

	public Transaction(Long userId, boolean isBought, String currency, BigDecimal amount) {
		this.userId = userId;
		this.isBought = isBought;
		this.currency = currency;
		this.amount = amount;
		this.transactionTime = new Date();
	}

}
