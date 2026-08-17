package com.demo.bankapp.exception;

import java.io.Serial;

public class BadCredentialsException extends RuntimeException {

	@Serial
	private static final long serialVersionUID = -349287396200850517L;

	public BadCredentialsException() {
		super("Bad Credentials.");
	}

	public BadCredentialsException(String message) {
		super("Bad Credentials: " + message);
	}

}
