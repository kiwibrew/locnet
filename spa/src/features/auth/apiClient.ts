import { ApiClient } from '../locnet/api-generated-client';


export class AuthenticatedApiClient extends ApiClient {
  override async ParseError(response: Response) {
    if (response.status === 401 && typeof window !== 'undefined') {
      window.location.assign('/');
    }
    return super.ParseError(response);
  }
}
