package com.demo.bankapp.exception;

import java.io.Serial;

public class DailyOperationLimitReachedException extends RuntimeException {

	@Serial
	private static final long serialVersionUID = -6260854119635270900L;

	public DailyOperationLimitReachedException() {
		super("Daily transaction limit is reached.");
	}

}
