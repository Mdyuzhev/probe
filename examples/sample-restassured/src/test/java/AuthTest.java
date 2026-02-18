import io.restassured.RestAssured;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;

public class AuthTest extends BaseTest {

    @Test
    public void operatorToken_accessAllowed_movements() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/movements")
        .then()
            .statusCode(200);
    }

    @Test
    public void managerToken_accessAllowed_reports() {
        given()
            .spec(managerSpec)
        .when()
            .get("/reports/monthly")
        .then()
            .statusCode(200);
    }

    @Test
    public void operatorToken_accessDenied_reports() {
        given()
            .spec(operatorSpec)
        .when()
            .get("/reports/monthly")
        .then()
            .statusCode(403)
            .body("error", equalTo("ACCESS_DENIED"));
    }

    @Test
    public void adminBasicAuth_accessAllowed() {
        given()
            .spec(baseSpec)
            .auth().basic("admin", "secret")
        .when()
            .get("/admin/users")
        .then()
            .statusCode(200);
    }

    @Test
    public void noAuth_publicEndpoint_allowed() {
        given()
            .spec(baseSpec)
        .when()
            .get("/reports/daily")
        .then()
            .statusCode(200);
    }

    @Test
    public void expiredToken_returns401() {
        given()
            .spec(baseSpec)
            .header("Authorization", "Bearer expired.token.value")
        .when()
            .get("/movements")
        .then()
            .statusCode(401)
            .body("error", equalTo("TOKEN_EXPIRED"));
    }

    @Test
    public void invalidToken_returns401() {
        given()
            .spec(baseSpec)
            .header("Authorization", "Bearer totally-invalid")
        .when()
            .get("/movements")
        .then()
            .statusCode(401)
            .body("error", equalTo("INVALID_TOKEN"));
    }

    @Test
    public void adminToken_accessAllowed_allResources() {
        given()
            .spec(adminSpec)
        .when()
            .get("/admin/users")
        .then()
            .statusCode(200);

        given()
            .spec(adminSpec)
        .when()
            .get("/reports/monthly")
        .then()
            .statusCode(200);
    }
}
