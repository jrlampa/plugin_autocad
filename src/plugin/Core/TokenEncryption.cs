using System;
using System.Security.Cryptography;
using System.Text;

namespace sisRUA.Core
{
    /// <summary>
    /// Provides Windows DPAPI-based encryption for sensitive data like authentication tokens.
    /// Uses Data Protection API (DPAPI) which encrypts data using user's Windows credentials.
    /// </summary>
    public static class TokenEncryption
    {
        private const string ENCRYPTION_PREFIX = "DPAPI:";
        
        /// <summary>
        /// Encrypts a token using Windows DPAPI.
        /// </summary>
        /// <param name="plainText">The token to encrypt</param>
        /// <returns>Encrypted token with DPAPI: prefix</returns>
        public static string Encrypt(string plainText)
        {
            if (string.IsNullOrWhiteSpace(plainText))
            {
                throw new ArgumentException("Token cannot be empty", nameof(plainText));
            }

            try
            {
                byte[] plainBytes = Encoding.UTF8.GetBytes(plainText);
                byte[] encryptedBytes = ProtectedData.Protect(
                    plainBytes,
                    optionalEntropy: null,
                    scope: DataProtectionScope.CurrentUser
                );
                
                string base64 = Convert.ToBase64String(encryptedBytes);
                return ENCRYPTION_PREFIX + base64;
            }
            catch (Exception ex)
            {
                throw new CryptographicException("Failed to encrypt token", ex);
            }
        }

        /// <summary>
        /// Decrypts a token that was encrypted with DPAPI.
        /// </summary>
        /// <param name="encryptedText">The encrypted token (with or without DPAPI: prefix)</param>
        /// <returns>Decrypted plaintext token</returns>
        public static string Decrypt(string encryptedText)
        {
            if (string.IsNullOrWhiteSpace(encryptedText))
            {
                throw new ArgumentException("Encrypted token cannot be empty", nameof(encryptedText));
            }

            try
            {
                // Check if token is encrypted
                if (!IsEncrypted(encryptedText))
                {
                    // Return as-is if not encrypted (backward compatibility)
                    return encryptedText;
                }

                // Remove prefix and decrypt
                string base64 = encryptedText.Substring(ENCRYPTION_PREFIX.Length);
                byte[] encryptedBytes = Convert.FromBase64String(base64);
                byte[] decryptedBytes = ProtectedData.Unprotect(
                    encryptedBytes,
                    optionalEntropy: null,
                    scope: DataProtectionScope.CurrentUser
                );
                
                return Encoding.UTF8.GetString(decryptedBytes);
            }
            catch (Exception ex)
            {
                throw new CryptographicException("Failed to decrypt token", ex);
            }
        }

        /// <summary>
        /// Checks if a token string is encrypted (has DPAPI: prefix).
        /// </summary>
        /// <param name="token">Token to check</param>
        /// <returns>True if encrypted, false otherwise</returns>
        public static bool IsEncrypted(string token)
        {
            return !string.IsNullOrWhiteSpace(token) && token.StartsWith(ENCRYPTION_PREFIX);
        }
    }
}
