export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** A request never reached the server: DNS/connection failure, CORS, or offline. */
export class NetworkError extends Error {
  constructor(message = "تعذر الاتصال بالخادم.") {
    super(message);
    this.name = "NetworkError";
  }
}

/** The request was aborted after exceeding the client-side timeout. */
export class TimeoutError extends Error {
  constructor(message = "انتهت مهلة الطلب.") {
    super(message);
    this.name = "TimeoutError";
  }
}
