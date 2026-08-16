package com.demo.bankapp.exception;

import java.io.Serial;

public class TransactionLimitException extends RuntimeException {

	@Serial
	private static final long serialVersionUID = -3442309139923977110L;

	public TransactionLimitException(String message) {
		super("Transaction Limit: " + message);
	}

}
