package com.demo.bankapp.model;

import java.math.BigDecimal;
import java.util.Date;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;

import lombok.Data;

@Data
@Entity
public class Transfer {

	private @Id @GeneratedValue Long id;
	private Long fromUserId;
	private Long toUserId;
	private String currency;
	private BigDecimal amount;
	private Date transferTime;

	private Transfer() {
	}

	public Transfer(Long fromUserId, Long toUserId, String currency, BigDecimal amount) {
		this.fromUserId = fromUserId;
		this.toUserId = toUserId;
		this.currency = currency;
		this.amount = amount;
		this.transferTime = new Date();
	}
}
