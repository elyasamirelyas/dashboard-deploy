package com.demo.bankapp.exception;

import java.io.Serial;

public class InsufficientFundsException extends RuntimeException {

	@Serial
	private static final long serialVersionUID = 8435355771655372975L;

	public InsufficientFundsException() {
		super("Insufficient Funds: Not enough TRY.");
	}

	public InsufficientFundsException(String currency) {
		super("Insufficient Funds: Your " + currency + " funds are not enough.");
	}

}
